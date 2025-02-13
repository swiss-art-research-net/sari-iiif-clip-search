def test_download(images_from_csv):
    images_from_csv.downloadImages()
    assert True

def test_process(images_from_csv):
    images_from_csv.processImages()
    assert True