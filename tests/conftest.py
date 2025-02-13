import pytest
import sys
import shutil
sys.path.append('src')
from sariIiifClipSearch import Images

@pytest.fixture(scope='module')
def temp_data_dir(tmpdir_factory):
    my_tmpdir = tmpdir_factory.mktemp("image_data")
    yield my_tmpdir 
    shutil.rmtree(str(my_tmpdir))

@pytest.fixture
def images_from_csv(temp_data_dir) -> Images:
    print(temp_data_dir)
    return Images(
        mode="CSV",
        dataDir=temp_data_dir,
        iiifColumn='iiif_url',
        # test_images.csv is a sample with the first 100 images from file `precomputedFeatures/bso/images.csv`
        imageCSV='tests/test_images.csv',
        threads=16,
        batchSize=64
    )