from StaticDataImport import XMLPATH
from xml.etree import cElementTree as ElementTree
import datetime
import os
import pandas
hdr = '{http://www.fpml.org/2008/FpML-4-5}'
hdr2 = '{http://www.standardbank.com/messagebus/core/FpML-4-5/extension}'


class TOMSTicket():
	def __init__(self, file='Alex_Bond_Example.xml'):
		self.root = ElementTree.parse(XMLPATH+file).getroot()
		self.tradeBundle = self.root.find('tradeBundles').find('tradeBundle')
		self.reference = self.tradeBundle.find('reference').text
		self.typology = self.tradeBundle.find('typology').text
		if self.typology != 'IRD-BONDS':
			return
		self.action = self.tradeBundle.find('action').text
		self.prev_reference = self.tradeBundle.find('previousReference').text
		self.action = self.tradeBundle.find('action').text
		self.trades = self.tradeBundle.find('trades')
		self.trades2 = self.trades.find(hdr + 'FpML')
		self.trades3 = self.trades2.find(hdr + 'trade')
		self.contract = self.trades3.find(hdr2 + 'bondContract')
		self.price = float(self.contract.findtext(hdr2+'cleanPrice'))
		self.notional = float(self.contract.find(hdr2+'notionalAmount').findtext(hdr + 'amount'))
		self.ccy = self.contract.find(hdr2+'notionalAmount').findtext(hdr + 'currency')
		self.dateSTR = self.trades3.find(hdr + 'tradeHeader').findtext(hdr2 + 'tradeInsertDate')
		self.frtdate = self.dateSTR[0:10] + ' ' + self.dateSTR[11:19]
		p1 = self.trades2.findall(hdr + 'party')[0]
		p2 = self.trades2.findall(hdr + 'party')[1]
		party1 = p1.findtext(hdr + 'partyName')
		party2 = p2.findtext(hdr + 'partyName')
		b = self.contract.find(hdr+'buyerPartyReference').items()[0][1]
		self.isin = self.contract.find(hdr2 + 'bond').findall(hdr + 'instrumentId')[2].text
		if b=='party1':
			self.buyer = party1
			self.seller = party2
		else:
			self.buyer = party2
			self.seller = party1
		bk1 = p1.findall(hdr+'partyId')[2].text
		bk2 = p2.findall(hdr+'partyId')[2].text
		firm1 = p1.findall(hdr+'partyId')[4].text
		firm2 = p1.findall(hdr+'partyId')[4].text
		if p1.find(hdr+'partyName').text == 'SBL':
			self.book = bk1[7:]
			self.counterparty = p2.find(hdr+'partyName').text
			if self.buyer == party1:
				self.quantity = self.notional
			else:
				self.quantity = - self.notional
		else:
			self.book = bk2[7:]
			self.counterparty = p1.find(hdr+'partyName').text
			if self.buyer == party2:
				self.quantity = self.notional
			else:
				self.quantity = - self.notional
		#trdnbr;insid;isin;trade_price;quantity;trade_time;portfolio;trade_curr;status;Trader;Counterparty;Salesperson;Sales Credit;Sales Credit MarkUp
		self.front_array = [self.reference, 'insid', self.isin, self.price, self.quantity, self.frtdate, self.book, self.ccy, 'dummystatus', 'TR', self.counterparty, 'SP', 0, 0]


	# def front_array(self):
	# 	# fra = []
	# 	# fra.append(self.reference)
	# 	# fra.append('insid')
	# 	# fra.append(self.isin)
	# 	# fra.append(self.price)
	# 	# fra.append(self.quantity)
	# 	# fra.append(self.frtdate)
	# 	# fra.append(self.book)
	# 	# fra.append(self.ccy)
	# 	# fra.append('dummystatus')
	# 	# fra.append('TR')
	# 	# fra.append(self.counterparty)
	# 	# fra.append('SP')
	# 	# fra.append(0)
	# 	# fra.append(0)
	# 	return [self.reference, 'insid', self.isin, self.price, self.quantity, self.frtdate, self.book, self.ccy, 'dummystatus', 'TR', self.counterparty, 'SP', 0, 0]
	# 	#return fra







def find_file_names(dt):
	allfiles = os.listdir(XMLPATH)
	allxmlfiles = filter(lambda x: x[-4:]=='.xml', allfiles)
	dtfiles = filter(lambda x: x[5:13]==dt.strftime('%Y%m%d'), allxmlfiles)
	return dtfiles


class RiskParser():

	def __init__(self):
		self.today = datetime.datetime.today()
		self.files = []
		self.all_xmls = []
		self.xmls = []
		pass

	def refresh(self):
		self.old_files = self.files
		self.files = find_file_names(self.today)
		newfiles =  list(set(self.files).difference(self.old_files))
		for f in newfiles:
			ticket = TOMSTicket(f)
			if ticket.typology == 'IRD-BONDS':
				self.all_xmls.append(ticket)

		#Clean cancels:
		addrefs = []
		cxlrefs = []
		for x in self.all_xmls:
			if x.action == 'ADD':
				addrefs.append(x.reference)
			if x.action == 'CANCEL':
				cxlrefs.append(x.reference)
		intrefs = set(addrefs).intersection(cxlrefs)
		newxmls = []
		for x in self.all_xmls:
			if (not(x.reference) in intrefs) and (x.action != 'CANCEL') and (x.frtdate[0:10]==self.today.strftime('%Y-%m-%d')):
				newxmls.append(x)
		self.xmls = newxmls
		d = [x.front_array for x in self.xmls]
		self.df = pandas.DataFrame(columns=['trdnbr', 'insid', 'isin', 'trade_price', 'quantity', 'trade_time', 'portfolio', 'trade_curr', 'status', 'Trader', 'Counterparty', 'Salesperson', 'Sales Credit', 'Sales Credit MarkUp'], data=d)
		self.df = self.df.set_index('trdnbr') #DO WE NEED THIS

		#self.to_df()


	def print_trade_list(self):
		for x in self.xmls:
			print x.front_array

	# def to_df(self):
	# 	#trdnbr;insid;isin;trade_price;quantity;trade_time;portfolio;trade_curr;status;Trader;Counterparty;Salesperson;Sales Credit;Sales Credit MarkUp
	# 	# d = []
	# 	# for x in self.xmls:
	# 	# 	d.append(x.front_array())
	# 	d = [x.front_array for x in self.xmls]
	# 	self.df = pandas.DataFrame(columns=['trdnbr', 'insid', 'isin', 'trade_price', 'quantity', 'trade_time', 'portfolio', 'trade_curr', 'status', 'Trader', 'Counterparty', 'Salesperson', 'Sales Credit', 'Sales Credit MarkUp'], data=d)
	# 	self.df = self.df.set_index('trdnbr') #DO WE NEED THIS



