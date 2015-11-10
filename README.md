# libcarta

Python library for analysing geotiffs


## Usage

```python
from libcarta import Carta, CartaArray, CartaAnalyser, Shape

tifs = ('carta2008.tif', 'carta2009.tif')
shape = Shape("mato-grosso/Mato_Grosso.shp")

print 'Cobertura'
for tif in tifs:
    print
    carta = Carta(tif)
    if shape.intersects(carta): #only process cartas that are in the shape
        print "Processing: " + tif
        carta = carta.clip(shape)
        analyser = CartaAnalyser(carta)
        analyser.print_classes() #analyser.classes() returns a dict
    print

print 'Transicao'
carta01 = Carta('carta2008.tif')
carta02 = Carta('carta2009.tif')

carta01 = carta01.clip(shape)
carta02 = carta02.clip(shape)

analyser = CartaAnalyser(carta01)
analyser.print_transitions(carta02) #analyser.transitions(carta02) returns a dict
```
