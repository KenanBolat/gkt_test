import numpy as np
from osgeo import gdal
import os
import rioxarray
import datetime

"""
Classification according to the classification mask generation defined in the following documentation
https://sentinels.copernicus.eu/web/sentinel/technical-guides/sentinel-2-msi/level-2a/algorithm

"""
NO_DATA = 0
SATURATED_OR_DEFECTIVE = 1
CAST_SHADOWS = 2
CLOUD_SHADOWS = 3
VEGETATION = 4
NOT_VEGETATED = 5
WATER = 6
UNCLASSIFIED = 7
CLOUD_MEDIUM_PROBABILITY = 8
CLOUD_HIGH_PROBABILITY = 9
THIN_CIRRUS = 10
SNOW_or_ICE = 11

"""Define functions to read the given data."""


def read_raster_data_gdal(filename):
    """Function the read the raster using gdal"""

    if os.path.isfile(filename):
        raster = gdal.Open(filename)
        return raster.ReadAsArray()
    else:
        assert f'File {filename} does not exists'


def read_raster_data_xr(filename):
    """Function the read the raster using xarray"""
    if os.path.isfile(filename):
        return rioxarray.open_rasterio(filename)
    else:
        assert f'File {filename} does not exists'


# Apply cloudmask using xarray method
def apply_cloud_mask(image_filename, scl_mask_filename, export=True):
    # Read Dataset using rasterio
    print("Processing started for applying cloud mask using xarray libraries ...")
    scl_dataset = read_raster_data_xr(scl_mask_filename)
    bands_dataset = read_raster_data_xr(image_filename)

    # define filter for the given classifications
    filter_values = (scl_dataset == VEGETATION) | (scl_dataset == NOT_VEGETATED) | (scl_dataset == UNCLASSIFIED)

    # Create mask using xarray filtering "where" method with required classifications
    mask = scl_dataset.where(filter_values, 0)

    # Export mask for visual comparison with the external GIS Applications
    if export:
        mask.rio.to_raster(os.path.join(processing_path, f'mask_{get_date_tag()}.tif'))

    # Apply mask to the bands
    masked_bands = bands_dataset.where(filter_values.values, 0)

    # Export masked out bands to a multilayered geotiff
    if export:
        masked_bands.rio.to_raster(os.path.join(processing_path, f'masked_bands_xr_{get_date_tag()}.tif'))

    print("Processing ended for applying cloud mask using xarray libraries ...")
    return masked_bands.values


# Apply cloudmask using GDAL method
def apply_cloud_mask_gdal(image_filename, scl_mask_filename, export=True):
    # Read raster data
    print("Processing started for applying cloud mask using GDAL libraries ...")
    raster_scl = read_raster_data_gdal(scl_mask_filename)
    raster_bands = read_raster_data_gdal(image_filename)

    # define filter for the given classifications
    filter_values = ((raster_scl == VEGETATION) | (raster_scl == NOT_VEGETATED) | (raster_scl == UNCLASSIFIED))

    # Create mask using list comprehension method
    masked_out_data = [np.nan_to_num(row * filter_values) for row in raster_bands]

    if export:

        print("Exporting data...")
        raster = gdal.Open(file_bands)

        driver = gdal.GetDriverByName("GTiff")
        rows, cols = raster_bands[0].shape

        out_data = driver.Create(os.path.join(processing_path, f"masked_bands_gdal_{get_date_tag()}.tif"),
                                 cols,
                                 rows,
                                 len(masked_out_data),
                                 gdal.GDT_Float32)

        out_data.SetGeoTransform(raster.GetGeoTransform())
        out_data.SetProjection(raster.GetProjection())

        for en, i in enumerate(masked_out_data):
            band = out_data.GetRasterBand(en + 1)
            band.WriteArray(i)

        band = None
        out_data = None
        raster = None
        print("Processing ended for applying cloud mask using GDAL libraries ...")
        return np.array(masked_out_data)


def get_date_tag(date_string_format="%Y%m%d-%H%M"):
    return datetime.datetime.now().strftime(date_string_format)


if __name__ == '__main__':
    start = datetime.datetime.now()

    # point this path to the folder where the required data resides s
    processing_path = r'./data'

    # data handling
    scl_filename = 'imageExample_SCL.tif'
    bands_filename = 'imageExample_Bands.tif'
    file_scl = os.path.join(processing_path, scl_filename)
    file_bands = os.path.join(processing_path, bands_filename)

    print(file_scl, file_bands)

    # Apply cloud mask with two different methodologies
    xr_result = apply_cloud_mask(file_bands, file_scl)
    gdal_result = apply_cloud_mask_gdal(file_bands, file_scl)

    print('Execution time for the first method:', str(datetime.datetime.now() - start))
