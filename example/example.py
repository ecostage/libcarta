import sys, os.path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
)
from libcarta import Carta, CartaArray, CartaAnalyser, Shape

tifs = ('carta2008.tif', 'carta_sul2008.tif', 'carta2009.tif', 'carta_sul2009.tif')
shape = Shape("mato-grosso/Mato_Grosso.shp")

print 'Cobertura'
for tif in tifs:
    print
    carta = Carta(tif)
    if shape.intersects(carta):
        print "Processing: " + tif
        carta = carta.clip(shape)
        analyser = CartaAnalyser(carta)
        # analyser.print_classes()
    print

print 'Transicao'
carta01 = Carta('carta2008.tif')
carta02 = Carta('carta2009.tif')

carta01 = carta01.clip(shape)
carta02 = carta02.clip(shape)

analyser = CartaAnalyser(carta)
analyser.print_transitions(carta02)
