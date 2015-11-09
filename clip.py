from shapely import geometry
from osgeo import gdal, gdalnumeric, ogr, osr
from PIL import Image, ImageDraw
import os, sys, numpy, utm
gdal.UseExceptions()


def imageToArray(i):
    """
    Converts a Python Imaging Library array to a
    gdalnumeric image.
    """
    a = gdalnumeric.fromstring(i.tobytes(),'b')
    a.shape = i.im.size[1], i.im.size[0]
    return a

def arrayToImage(a):
    """
    Converts a gdalnumeric array to a
    Python Imaging Library Image.
    """
    i = Image.fromstring('L',(a.shape[1],a.shape[0]),
                            (a.astype('b')).tobytes())
    return i

positive = lambda a: (abs(a)+a)/2

def coord2pixel(gm, coord):
    """
    Uses a gdal geomatrix (gdal.GetGeoTransform()) to calculate
    the pixel location of a geospatial coordinate
    """
    x1 = gm[0]
    y1 = gm[3]
    width = (gm[1])
    height = (gm[5])

    pixel = int((coord[0] - x1) / width)
    line = int((coord[1] - y1) / height)

    return ((pixel), (line))


class Raster:
    def __init__(self, path):
        new_path = self.reproject(path)
        self.ds = gdal.Open(new_path)
        self.geomatrix = self.ds.GetGeoTransform()
        self.filepath = new_path

    def __del__(self):
        self.cleanup()

    def reproject(self, path):
        new_filename = 'tmp_'+os.path.split(path)[-1]
        new_path = list(os.path.split(path)[:-1])
        if new_path[0] == '':
            new_path[0] = new_filename
        else:
            new_path.append(new_filename)
        new_path = "/".join(new_path)
        os.system('gdalwarp %s %s -t_srs "+proj=longlat +ellps=WGS84"' % (path, new_path))
        return new_path

    def cleanup(self):
        os.unlink(self.filepath)

    def bounds(self):
        width = self.ds.RasterXSize
        height = self.ds.RasterYSize
        gm = self.geomatrix

        x1 = gm[0]
        y1 = gm[3]
        x2 = x1 + width * gm[1] + (gm[1] / 2)
        y2 = y1 + height * gm[5] + (gm[5] / 2)

        return ((x1, y1), (x2, y2))

    def coord2pixel(self, coord):
        return coord2pixel(self.geomatrix, coord)

    def clip_as_array(self, shape):
        ul, lr = self.clipbounds(shape) #upper left, lower right
        ulx, uly = ul
        lrx, lry = lr

        width = int(lrx - ulx)
        height = int(lry - uly)

        # Map points to pixels for drawing the
        # boundary on a blank 8-bit,
        # black and white, mask image.
        pixels = []
        shape_geom = shape.polygon.GetGeometryRef()
        shape_points = shape_geom.GetGeometryRef(0)

        for p in range(shape_points.GetPointCount()):
            p = (shape_points.GetX(p), shape_points.GetY(p))
            pxx, pxy = self.coord2pixel(p)

            if pxx < ulx and pxy < uly:
                pixels.append((ulx, uly))
            elif pxx < ulx and pxy >= uly:
                pixels.append((ulx, pxy))
            elif pxx >= ulx and pxy < uly:
                pixels.append((pxx, uly))
            elif pxx > lrx and pxy > lry:
                pixels.append((lrx, uly))
            elif pxx > lrx and pxy <= lry:
                pixels.append((lrx, pxy))
            elif pxx <= lrx and pxy > lry:
                pixels.append((pxx, lry))
            else:
                pixels.append((pxx, pxy))

        image = Image.new("L", (width, height), 1)
        rasterize = ImageDraw.Draw(image)
        rasterize.polygon(pixels, 0)
        mask = imageToArray(image)

        data = gdalnumeric.LoadFile(self.filepath)
        clipped_data = data[uly:lry, ulx:lrx]

        gdal.ErrorReset()

        return gdalnumeric.choose(mask,
                (clipped_data, 255)).astype(gdalnumeric.uint8)

    def clip(self, shape, outfile="out.tiff"):
        clipped_data = self.clip_as_array(shape)
        band = self.ds.GetRasterBand(1)
        driver = gdal.GetDriverByName('GTiff')
        outds = driver.Create(outfile, self.ds.RasterXSize,
                              self.ds.RasterYSize, 1, band.DataType)
        gdalnumeric.CopyDatasetInfo(self.ds, outds)
        outband = outds.GetRasterBand(1)
        gdalnumeric.BandWriteArray(outband, clipped_data)
        gdal.ErrorReset()

    def pxbounds(self):
        bs = self.bounds()
        p1 = self.coord2pixel(bs[0])
        p2 = self.coord2pixel(bs[1])
        return (p1, p2)

    def clipbounds(self, shape):
        bs = shape.bounds()
        ul, lr = self.pxbounds()

        p1 = self.coord2pixel(bs[0])
        p2 = self.coord2pixel(bs[1])

        p1 = (max(ul[0], positive(p1[0])), max(ul[1], positive(p1[1])))
        p2 = (min(lr[0], abs(p2[0])), min(lr[1], abs(p2[1])))

        return (p1, p2)


class Shape:
    def __init__(self, path):
        self.ds = ogr.Open(path)
        self.layer = self.ds.GetLayer(
            os.path.split(os.path.splitext(path)[0])[1]
        )
        self.polygon = self.layer.GetNextFeature()

    def bounds(self):
        x1, x2, y2, y1 = self.layer.GetExtent()
        return ((x1, y1), (x2, y2))

    def intersects(self, carta):
        ul, lr = carta.bounds()
        ur, ll, = ((lr[0], ul[1]), (ul[0], lr[1]))

        shape_geom = self.polygon.GetGeometryRef()
        shape_points = shape_geom.GetGeometryRef(0)
        carta_polygon = geometry.Polygon((ul, ur, lr, ll))

        points = []
        for p in range(shape_points.GetPointCount()):
            points.append((shape_points.GetX(p), shape_points.GetY(p)))

        shape_polygon = geometry.Polygon(points)

        return shape_polygon.intersects(carta_polygon)


def main(shapefile_path, raster_path):
    raster = Raster(raster_path)
    shape = Shape(shapefile_path)
    raster.clip(shape)


if __name__ == '__main__':
    #
    # example run : $ python _clip.py /<full-path>/<shapefile-name>.shp /<full-path>/<raster-name>.tif
    #
    if len( sys.argv ) < 2:
        print "[ ERROR ] you must two args. 1) the full shapefile path and 2) the full raster path"
        sys.exit( 1 )

    main( sys.argv[1], sys.argv[2] )
