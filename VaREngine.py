import pandas
import datetime

from StaticDataImport import MYPATH, DEFPATH, ccy, allisins, bonds


class VaREngine():
	def __init__(self, file=None, start_date=None,end_date=None,positions=None):

		self.positions = positions.copy()
		self.var_window = pandas.bdate_range(datetime.datetime(2014,10,13),datetime.datetime(2015,9,15))
		self.svar_window = pandas.bdate_range(datetime.datetime(2014,9,11),datetime.datetime(2015,8,31))
		pass

	def build_proxies(self):
		self.positions['ISIN'] = bonds['REGS']
		self.clean_proxy_file()
		self.positions[['proxyBond','proxyISIN']].join()
		pass

	def clean_proxy_file(self):
		self.proxyfile = pandas.read_csv(DEFPATH+'ProxyReport.csv',index_col=0)
		self.proxyfil = self.proxyfile[(self.proxyfile['SVAR PROXY STEP USED']!=1) | (self.proxyfile['Proxy step used']!=1)]
		self.proxyfile['ISIN'] = self.proxyfile.index.str[-12:]
		self.proxyfile['is_pos'] = self.proxyfile['ISIN'].apply(lambda x:x in self.positions['ISIN'])
		self.proxyfile = self.proxyfile[self.proxyfile['is_pos']]
		self.proxyfile['Bond'] = self.proxyfile['ISIN'].replace(allisins)
		self.proxyfile['proxyISIN'] = self.proxyfile['Proxy ADO longname'].str[-12:]
		self.proxyfile['proxyBond'] = self.proxyfile['proxyISIN'].replace(allisins)
		self.proxyfile['SproxyISIN'] = self.proxyfile['SVAR PROXY ADO LONGNAME'].str[-12:]
		self.proxyfile['SproxyBond'] = self.proxyfile['SproxyISIN'].replace(allisins)
		self.proxyfile.set_index('Bond',inplace=True)
		self.proxyfile = self.proxyfile[['ISIN','proxyBond','proxyISIN','SproxyBond','SproxyISIN']]

	def build_history(self):
		self.bondisins = list(set(self.positions['proxyISIN']+' Corp')+set(self.positions['SproxyISIN']+' Corp'))
		sd = min(self.var_window.index[0],self.svar_window.index[0])+datetime.timedelta(days=-30)
	    blpts = blpapiwrapper.BLPTS(self.bondisins,'PX_LAST',startDate=sd,endDate=datetime.datetime.today(),periodicity='DAILY')
        hr = HistoryRequest(self.bondisins)
        blpts.register(hr)
        blpts.get()
        blpts.closeSession()
        self.price_history = pandas.DataFrame(index=pandas.bdate_range(sd,datetime.datetime.today()))
        for isin in self.bondisins:# this is needed as not all time series end at the same point.
            self.price_history[isin[-5]] = hr.bondisinsDC[isin]
        self.price_history.fillna(method='pad',inplace=True)
        self.d_price_history = self.price_history-self.price_history.iloc[-1]
        self.d10_price_history = self.price_history-self.price_history.iloc[-10]


    def dot_product(self,history):
    	return self.positions['Qty'].dot(history)
    	pass

    def build_strips(self):
    	self.var_positions=self.positions.reindex
    	self.one_day_var = []
    	self.one_day_svar = []
    	self.ten_day_var = []
    	self.ten_day_svar = []
    	pass

	def get_var(self,percentile):
		pass

	def get_strip(date):
		pass


class HistoryRequest(blpapiwrapper.Observer):
    """HistoryRequest Object (Inherits from blpapiwrapper.Observer). Object to stream and record history data from Bloomberg.
    """
    def __init__(self,bondisins):
        self.bondisinsDC = {}
    def update(self, *args, **kwargs):
        if kwargs['field'] != 'ALL':
            self.bondisinsDC[kwargs['security']]=kwargs['data']
