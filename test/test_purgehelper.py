import pytest, sys, os, time, datetime, pathlib, tempfile
from pprint import PrettyPrinter as pp
#needed to import functions in odd paths
sys.path.append(os.path.abspath('./'))

from purgehelper import parse_args, PurgeObject, PurgeError, PurgeNotFileError

@pytest.mark.parametrize("InvalidArgs", [
                                 ('--days', '5'),
                                 ('--file', '/tmp/data'),
                                 ('--scanident', '1-1-999'),
                                 ('--scanident', '1-1-999', '--file', '/tmp/data'),
                                ])
def test_missing_args(InvalidArgs):
    with pytest.raises(SystemExit) as e:
         args = parse_args(InvalidArgs)
         assert isinstance(e.__context__, argparse.ArgumentError)
    assert e.type == SystemExit

@pytest.mark.parametrize("ValidArgs", [
                                 [('--file', '/tmp/data', '--days', '5', '--scanident', '1-1-999'),
                                  ('/tmp/data', '5', '1-1-999')]
                                ])
def test_valid_args(ValidArgs):
    args = parse_args(ValidArgs[0])
    assert args.file == ValidArgs[1][0]
    assert args.days == int(ValidArgs[1][1])
    assert args.scanident == ValidArgs[1][2]



@pytest.fixture
def agedfile(tmp_path):
    """setup a number of example file 75 days last accessed"""
    # return as a string as PurgeObject expects a string
    f = tmp_path / "75day-file.txt"
    f.touch()
    today = datetime.date.today()
    delta = datetime.timedelta(days=75)
    delta = today-delta
    aTime = time.mktime(delta.timetuple())
    os.utime(f, (aTime, aTime))  # os.utime takes touple (atime, mtime)
    return f.resolve()

##@pytest.mark.parametrize("strpath", [agedfile])
#@pytest.mark.parametrize("strpath", [agedfile, '/garbage/path/file.txt'])
#def test_PurgeObject(strpath, tmp_path):
#    print(dir(strpath))
#    print(type(strpath))
#    if isinstance(strpath, function):
#       po = PurgeObject(path=strpath(tmp_path))
#    else:
#       po = PurgeObject(path=strpath)
#      
#    print(po)


## currently need to break out the fixture input and string inputs TODO
#@pytest.mark.parametrize("strpath", [agedfile])
def test_PurgeObject(agedfile):
    po = PurgeObject(path=agedfile, days=5, purge=True)
    assert po._path == agedfile     # file should exist and load into object

## currently need to break out the fixture input and string inputs TODO
@pytest.mark.parametrize("strpath", ['/garbage/path/file.txt'])
def test_PurgeObject_bad(strpath):
    """make sure to bail if file doesn't exist"""
    with pytest.raises(PurgeNotFileError):
        po = PurgeObject(path=strpath, days=5, purge=True)


@pytest.mark.parametrize("kwargs", [
                { 'days': 5,  'stagepath': '/tmp', 'purge': True},   # can't stage and purge
                { 'purge': False},     		# days must be given to build rules
                {},  			   	# days must be given to build rules (no args)
                { 'days': 5 }  		        # valid days, but no stagepath or purge
                ])
def test_purgeObject_bad_params(agedfile, kwargs):
    """check that we don't do anything if invalid combinations are not false"""
    with pytest.raises(PurgeError):
        po = PurgeObject(path=agedfile, **kwargs)

@pytest.fixture
def stagepath():
    """create extra tmp path as only one tmp_path can exist at a time"""
  #  with tempfile.TemporaryDirectory() as stagepath:
  #       path =  pathlib.Path(stagepath)
  #       yield path
    return tempfile.mkdtemp()

@pytest.mark.parametrize("kwargs", [
                { 'days': 60}  # days over
                ])     
def test_purgeObject_stage(agedfile, stagepath, kwargs):
    """ check staging of old files"""
    po = PurgeObject(path=agedfile, stagepath=stagepath, **kwargs)
    num_f_before = 0
    for f in pathlib.Path(agedfile).parent.iterdir():
       if f.is_file():
          num_f_before += 1
 
    print(f"Number of files before: {num_f_before}")

    po.applyrules()  # take action on file
    
    # count number of files after and at destimation
    num_f_after = 0
    for f in pathlib.Path(agedfile).parent.iterdir():
       if f.is_file():
          num_f_after += 1

    print(f"Number of files after: {num_f_after}")

    print(f"Stage: {stagepath}")
    stagepath = pathlib.Path(stagepath)
    num_f_dest = 0
    for f in stagepath.glob('**/*'):
       if f.is_file():
          num_f_dest += 1

    print(f"Number of files staged: {num_f_dest}")
