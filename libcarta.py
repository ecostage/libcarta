from optparse import OptionParser
import json
from osgeo import gdal
import sys
from clip import Raster, Shape
gdal.UseExceptions()

class Carta:
    def __init__(self, filepath, options=None):
        self.raster = Raster(filepath)
        self.ds = self.raster.ds
        self.options = options

    def bounds(self):
        return self.raster.bounds()

    def clip(self, shape):
        return CartaArray(self.raster.clip_as_array(shape), self.options)

    def band(self):
        try:
            return self.options.band
        except:
            return 1

    def iter_band_blocks(self):
        band = self.ds.GetRasterBand(self.band())
        bSize = band.GetBlockSize()[0]
        rows = band.YSize
        cols = band.XSize

        for i in range(0, rows, bSize):
            if i + bSize < rows:
                numRows = bSize
            else:
                numRows = rows - i

            for j in range(0, cols, bSize):
                if j + bSize < cols:
                    numCols = bSize
                else:
                    numCols = cols - j
                block = band.ReadAsArray(j, i, numCols, numRows)
                yield(block)


class CartaArray:
    def __init__(self, ds, options=None):
        self.ds = ds
        self.options = options

    def iter_band_blocks(self):
        yield(self.ds)


class CartaAnalyser:
    def __init__(self, carta, options=None):
        self.carta = carta
        self.options = options

    def no_data_value(self):
        try:
            return self.options.no_data_value
        except:
            return 255

    def classes(self):
        classes = {}
        for block in self.carta.iter_band_blocks():
            for row in block:
                for px in row:
                    try:
                        classes[px] += 1
                    except:
                        classes[px] = 1

        if self.no_data_value() in classes:
            del classes[self.no_data_value()]

        return classes

    def transitions(self, comparison_carta):
        transitions = []

        def add_transition(_from, to):
            no_data_value = self.no_data_value()
            if _from == no_data_value or to == no_data_value:
                return False
            for (i, transition) in enumerate(transitions):
                if transition['from'] == _from and transition['to'] == to:
                    transition['value'] += 1
                    transitions[i] == transition
                    return True
            transitions.append({
                'from': _from,
                'to': to,
                'value': 1
            })
            return True

        comparison_blocks = list(comparison_carta.iter_band_blocks())
        for (i, block) in enumerate(self.carta.iter_band_blocks()):
            comparison_block = comparison_blocks[i]
            for (row_i, row) in enumerate(block):
                for (px_i, px) in enumerate(row):
                    comparison_px = comparison_block[row_i][px_i]
                    if px != comparison_px:
                        add_transition(px, comparison_px)

        return transitions

    def print_transitions(self, compare_carta):
        for transition in self.transitions(compare_carta):
            ha_value = ((30*30) * transition['value']) / 10000.0
            print "%s -> %s: %f" % (transition['from'], transition['to'], ha_value)

    def print_classes(self):
        classes = self.classes()
        for (_class, value) in classes.iteritems():
            ha_value = ((30*30) * value) / 10000.0
            print "%s: %f" % (_class, ha_value)

def main():
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filepath", metavar="file")
    parser.add_option("-c", "--compare", dest="compare_filepath", metavar="file")
    parser.add_option("--no-data-value", dest="no_data_value", default=255)
    parser.add_option("-b", "--band", dest="band", default=1)
    parser.add_option("-q", "--quiet", dest="quiet", default=False)
    (options, args) = parser.parse_args()

    carta = Carta(options.filepath, options)
    compare_carta = Carta(options.compare_filepath, options)

    analyser = CartaAnalyser(carta, options)
    analyser.print_transitions(compare_carta)
    analyser.print_classes()

if __name__ == '__main__':
    main()
