from StaticDataImport import DEFPATH
from xml.etree import cElementTree as ElementTree


class TOMSTicket():
	def __init__(self,file='Alex_Bond_Example.xml'):
		root = ElementTree.parse(DEFPATH+file).getroot()
		tradeBundle = root.find('tradeBundles').find('tradeBundle')
		self.toms_reference = trade.find('reference').text