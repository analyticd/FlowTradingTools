import pandas
import os
import datetime
import matplotlib
import matplotlib.pyplot as plt
from StaticDataImport import MYPATH, TEMPPATH, THPATH, DEFPATH, UATPATH, ccy, countries, bonds, LDNFLOWBOOKS, isinsregs, isins144a, allisins, MAPATH, counterparties, BBGPATH, STAGINGPATH
import blpapiwrapper
from shutil import copy2

BASE_COLUMNS = [u'Status', u'Client', u'Dealer', u'Bid/Offer', u'Issuer', u'Ticker',
u'COUPON', u'Maturity', u'Level', u'Adj. Level', u'Benchmark', u'Price',
u'Cover', u'CUSIP', u'ISIN', u'Inquiry Timestamp', u'Trade DateTime',
u'CLT Trader', u'DLR Trader', u'Settlement Date', u'Inquiry ID',
u'Trade ID', u'LinkID', u'BM CUSIP', u'BM ISIN', u'BM Price', u'Book',
u'Salesperson', u'Yield', u'Z Spread', u'Net Money', u'Sector',
u'Product', u'Protocol', u'Currency', u'Market Category',
u'Inquiry Volume', u'Local Inquiry Volume',
u'Counterparty Response Volume', u'Local Trade Volume']

IMPORT_DIC = dict(zip(BASE_COLUMNS,[object for i in BASE_COLUMNS]))
IMPORT_DIC[u'COUPON'] = pandas.np.float64
IMPORT_DIC[u'Level'] = pandas.np.float64
IMPORT_DIC[u'Adj. Level'] = pandas.np.float64
IMPORT_DIC[u'Price'] = pandas.np.float64
IMPORT_DIC[u'Cover'] = pandas.np.float64
#IMPORT_DIC[u'Inquiry Timestamp'] = pandas.np.datetime64
IMPORT_DIC[u'Inquiry ID'] = pandas.np.float64
IMPORT_DIC[u'Trade ID'] = pandas.np.float64
IMPORT_DIC[u'BM Price'] = pandas.np.float64
IMPORT_DIC[u'Yield'] = pandas.np.float64
IMPORT_DIC[u'Z Spread'] = pandas.np.float64
IMPORT_DIC[u'Net Money'] = pandas.np.float64
IMPORT_DIC[u'Inquiry Volume'] = pandas.np.float64
IMPORT_DIC[u'Local Inquiry Volume'] = pandas.np.float64
IMPORT_DIC[u'Counterparty Response Volume'] = pandas.np.float64
IMPORT_DIC[u'Local Trade Volume'] = pandas.np.float64

USECOLS = [u'Status',u'Client',u'CLT Trader',u'Bid/Offer',u'ISIN',u'Inquiry Timestamp',u'Currency',u'Local Inquiry Volume',u'Product']
#USECOLSID = []
#for c in USECOLS:

BASE_COLUMNS_BBG = [u'Time', u'Security', u'DlrSide', u'Qty (M)', u'Price (Dec)', u'Price',
       u'Status', u'Cover', u'Cover 2', u'Customer', u'Yield', u'ISIN',
       u'BrkrName', u'Alloc Status', u'Trade Dt', u'Ord/Inq', u'Platform',
       u'App', u'UserName', u'Dlr Alias', u'Brkr', u'Seq#']

IMPORT_DIC_BBG = dict(zip(BASE_COLUMNS_BBG,[object for i in BASE_COLUMNS_BBG]))
IMPORT_DIC_BBG[u'Qty (M)'] = pandas.np.float64
IMPORT_DIC_BBG[u'Price (Dec)'] = pandas.np.float64
IMPORT_DIC_BBG[u'Price'] = pandas.np.float64
#IMPORT_DIC_BBG[u'Cover'] = pandas.np.float64
#IMPORT_DIC_BBG[u'Cover 2'] = pandas.np.float64
IMPORT_DIC_BBG[u'Seq#'] = pandas.np.float64


class FullMarketAxessData():

    def __init__(self, rebuild=False, forceLastDay=False):
        self.savepath = MAPATH+'ma_full.csvz'
        if rebuild or (not os.path.exists(self.savepath)):
            self.load_files_full()
        elif datetime.datetime.fromtimestamp(os.path.getmtime(self.savepath)).date()<datetime.datetime.today().date() or forceLastDay:
            self.load_files()
        else:
            self.df = pandas.read_csv(self.savepath, parse_dates=['Inquiry Timestamp'], index_col=0, compression='bz2', dtype=IMPORT_DIC, low_memory=False)#, usecols=USECOLS)
        self.df = self.df[['Status','Client','CLT Trader','Bid/Offer','ISIN','Inquiry Timestamp','Currency','Local Inquiry Volume','Product']]
        self.df = self.df[self.df['Product']=='Emerging Markets'].copy()
        del self.df['Product']
        self.df.rename(columns = {'Local Inquiry Volume':'AbsQty', 'Currency':'CCY','Inquiry Timestamp':'Date'}, inplace = True)
        self.df = self.df[self.df['CCY'].isin(['USD','EUR','CHF','GBP'])]
        self.df = self.df.join(allisins, on = 'ISIN')
        ma_counterparties = counterparties[counterparties['MAName'].notnull()]
        ma_counterparties.set_index('MAName', inplace=True)
        self.df = self.df.join(ma_counterparties['Counterparty'],on='Client')
        self.df = self.df.join(ccy['2017'],on='CCY')
        #self.df['AbsUSDQty'] = self.df.apply(lambda row:row['AbsQty']/ccy.loc[row['CCY'],'2016'],axis=1) ##TOO SLOW
        self.df['AbsUSDQty'] = self.df['AbsQty'] / self.df['2017']
        del self.df['2017']
        self.df['USDQty'] = self.df['AbsUSDQty']
        self.df.loc[self.df['Bid/Offer']=='Offer','USDQty'] = -self.df.loc[self.df['Bid/Offer']=='Offer','USDQty']
        self.df = self.df.join(bonds[['TICKER','CNTRY_OF_RISK']],on='Bond')
        self.df.rename(columns={'TICKER':'Issuer','CNTRY_OF_RISK':'Country'},inplace=True)
        self.df = self.df.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')
        self.df['DateDT'] = self.df['Date']
        #self.df['DateDT'] = pandas.to_datetime(self.df['Date'],format='%d/%m/%Y %H:%M:%S')
        self.df['Date'] = self.df['DateDT'].apply(lambda x:x.date())
        # we filter for error trades
        self.df = self.df[self.df['AbsUSDQty']<100000] # filtering for likely error trades
        #del self.df['Client'] - WE NEED THIS SO WE CAN LOOK FOR NAN

    def load_files_full(self):
        self.df = pandas.DataFrame(columns = BASE_COLUMNS)
        start_date = datetime.datetime(2016,2,9)
        end_date = datetime.datetime.today()
        day_count = (end_date - start_date).days + 1 # to include today
        #last_date='null'
        for single_date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            try:
                single_date_str = single_date.strftime('%Y-%m-%d')
                daily = pandas.read_excel(MAPATH+'CounterParty Inquiry Blotter - Standard Bank - '+single_date_str+'.xlsx',skiprows=[0,1])
                self.df = self.df.append(daily,ignore_index=True)
                #last_date_str = single_date_str
            except IOError as e:
                pass
        #self.df.to_csv(MAPATH+'ma_full_'+last_date_str+'.csv')
        self.df.to_csv(self.savepath, compression = 'bz2')

    def load_files(self):
        self.df = pandas.read_csv(self.savepath, parse_dates=['Inquiry Timestamp'], index_col=0, compression = 'bz2', dtype=IMPORT_DIC)
        last_existing_date = (self.df.iloc[-1]['Inquiry Timestamp']).date()
        start_date = last_existing_date + datetime.timedelta(1)
        end_date = datetime.date.today()
        day_count = (end_date - start_date).days + 1 # to include today
        for single_date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            try:
                single_date_str = single_date.strftime('%Y-%m-%d')
                daily = pandas.read_excel(MAPATH+'CounterParty Inquiry Blotter - Standard Bank - '+single_date_str+'.xlsx',skiprows=[0,1])
                self.df = self.df.append(daily,ignore_index=True)
            except IOError as e:
                pass
        self.df.to_csv(self.savepath, compression = 'bz2')
        pass



    def plot_client_enquiries(self, style='net', region='all'):
        if style == 'net':
            if region == 'all':
                subdf = pandas.DataFrame((-self.df['USDQty'].groupby(self.df['Date']).sum()/1000.))
            else:
                grp = self.df.groupby(['Date','Region'])
                data = -grp['USDQty'].sum()/1000.
                data = data.unstack()
                subdf = pandas.DataFrame(data[region])
                subdf.rename(columns={region:'USDQty'},inplace = True)
            ax = plt.axes()
            subdf['10dEWMA'] = pandas.ewma(subdf['USDQty'],10)
            ax = plt.axes()
            subdf['10dEWMA'].plot(ax=ax,color='red',lw=3,title='Net USD enquiry volume (MM) and 10 day EWMA')
            ax.bar(subdf.index,subdf['USDQty'],align='center')
            xmin,xmax = ax.get_xlim()
            newlim = (xmin, matplotlib.dates.date2num(matplotlib.dates.num2date(xmax) + datetime.timedelta(3)))
            ax.set_xlim(newlim)
        elif style =='full':
            grp = self.df[['AbsUSDQty','USDQty']].groupby(self.df['Date']).sum()/1000.
            grp['USDQty'] = -1.*grp['USDQty']
            grp.rename(columns={'USDQty':'Net','AbsUSDQty':'Gross'},inplace=True)
            grp.tail(30).plot(kind='bar', title='USD enquiry volume (MM)', grid=True)
        elif style =='region':
            grp = self.df.groupby(['Date','Region'])
            data = -grp['USDQty'].sum()
            data = data.unstack()
            data[['Africa','CEE','CIS']].tail(30).plot(kind = 'bar', title='Net USD enquiry volume (MM)', grid=True)
        else:
            pass
        plt.show()
        pass


    def total_report(self, dt):
        dts = dt.date()
        subdf = self.df.loc[self.df['Date']==dts]
        grp = subdf.groupby('CCY')
        print grp[['USDQty','AbsQty']].sum().applymap(lambda y:'{:,.0f}'.format(y))
        pass

    def client_report(self, dt):
        dts = dt.date()
        subdf = self.df.loc[self.df['Date']==dts]
        grp1 = subdf.groupby('Counterparty')
        sg = grp1.sum()
        out = sg[(sg['USDQty']>=2000) | (sg['USDQty']<-2000)]
        print out['USDQty'].apply(lambda y:'{:,.0f}'.format(y))
        #print ''
        #grp2=self.df.groupby(['MACounterparty','Country'])
        #print grp2[['USDQty']].sum().applymap(lambda y:'{:,.2f}'.format(y))
        pass

    def region_report(self, dt):
        dts = dt.date()
        subdf = self.df.loc[self.df['Date']==dts]
        grp1 = subdf.groupby('Region')
        print grp1[['USDQty']].sum().loc[['Africa','CEE','CIS']].applymap(lambda y:'{:,.0f}'.format(y))
        print ''
        grp2 = subdf.groupby(['Region','Country'])
        print grp2[['USDQty']].sum().loc[['Africa','CEE','CIS']].applymap(lambda y:'{:,.0f}'.format(y))
        pass

    def full_report(self, dt):
        print '=============================================='
        print 'Total enquiries:'
        print '=============================================='
        self.total_report(dt)
        print ''
        print '=============================================='
        print 'Enquiries by region (only accurate for EMEA):'
        print '=============================================='
        self.region_report(dt)
        print ''
        print '=============================================='
        print 'Enquiries by client (showing >$2mm net):'
        print '=============================================='
        self.client_report(dt)
        print ''
        pass

    def hot_and_cold(self, days, tail):
        dt = datetime.datetime.now() - datetime.timedelta(days=days)
        dt = dt.replace(hour=0,  minute=0)
        subdf = self.df.loc[self.df['DateDT'] >= dt]
        grp = subdf.groupby(['Bond'])
        a = grp['AbsQty'].agg(['sum','count'])
        out = a.sort_values('sum').tail(tail)
        out['net'] = grp['USDQty'].sum()
        grp2 = subdf[subdf['USDQty']<0].groupby('Bond')
        b = grp2['USDQty'].agg(['sum','count'])
        out['ClientBuys'] = b['count']
        out.fillna(0, inplace=True)
        out = out.sort_values('sum',ascending=False)
        prettyout=out.copy()
        prettyout['sum'] = prettyout['sum'].apply(lambda y:'{:,.0f}'.format(y))
        prettyout['net'] = prettyout['net'].apply(lambda y:'{:,.0f}'.format(y))
        print prettyout
        return out




class FullBBGALLQData():

    def __init__(self, rebuild=False, forceLastDay=False):
        self.savepath = BBGPATH+'bbg_full.csvz'
        if rebuild or (not os.path.exists(self.savepath)):
            self.load_files_full()
        elif datetime.datetime.fromtimestamp(os.path.getmtime(self.savepath)).date()<datetime.datetime.today().date() or forceLastDay:
            self.load_files()
        else:
            self.df = pandas.read_csv(self.savepath, index_col=0, compression='bz2', dtype=IMPORT_DIC_BBG)#, usecols=USECOLS)
        

        self.df = self.df[['Time','DlrSide','Qty (M)','Status','Customer', 'ISIN','Trade Dt','UserName']]
        self.df = self.df.copy()
        self.df['strDate'] = self.df['Trade Dt'] + ' ' + self.df['Time']
        # Convert NY time to UK time - adding 5h which is not always correct (DST)
        self.df['DateDT'] = pandas.to_datetime(self.df['strDate']) + pandas.Timedelta(hours=5)
        self.df['Date'] = self.df['DateDT'].apply(lambda x: x.date())
        # self.df['Time'] =  self.df['DateDT'].dt.strftime('%X')
        del self.df['strDate']
        del self.df['Time']
        del self.df['Trade Dt']
        #
        self.df = self.df.join(allisins, on = 'ISIN')
        self.df = self.df.join(bonds['CRNCY'], on = 'Bond')
        self.df.rename(columns = {'Qty (M)':'AbsQty', 'Customer': 'Client', 'CRNCY': 'CCY', 'DlrSide': 'Bid/Offer', 'UserName': 'CLT Trader'}, inplace = True)
        bbg_counterparties = counterparties[counterparties['BBGName'].notnull()]
        bbg_counterparties.set_index('BBGName', inplace=True)
        self.df = self.df.join(bbg_counterparties['Counterparty'], on='Client')
        self.df = self.df.join(ccy['2017'], on='CCY')
        #self.df['AbsUSDQty'] = self.df.apply(lambda row:row['AbsQty']/ccy.loc[row['CCY'],'2016'],axis=1) ##TOO SLOW
        self.df['AbsUSDQty'] = self.df['AbsQty'] / self.df['2017']
        del self.df['2017']
        self.df['USDQty'] = self.df['AbsUSDQty']
        self.df.loc[self.df['Bid/Offer']=='S','USDQty'] = -self.df.loc[self.df['Bid/Offer']=='S','USDQty']
        self.df = self.df.join(bonds[['TICKER','CNTRY_OF_RISK']],on='Bond')
        self.df.rename(columns={'TICKER':'Issuer','CNTRY_OF_RISK':'Country'},inplace=True)
        self.df = self.df.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')

    def load_files_full(self):
        self.df = pandas.DataFrame(columns = BASE_COLUMNS_BBG)
        start_date = datetime.datetime(2017,5,7)
        end_date = datetime.datetime.today()
        day_count = (end_date - start_date).days + 1 # to include today
        #last_date='null'
        for single_date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            try:
                single_date_str = single_date.strftime('%Y%m%d')
                daily = pandas.read_csv(BBGPATH+'ICBCSFTP-'+single_date_str)
                self.df = self.df.append(daily,ignore_index=True)
                #last_date_str = single_date_str
            except IOError as e:
                pass
        #self.df.to_csv(MAPATH+'ma_full_'+last_date_str+'.csv')
        self.df.to_csv(self.savepath, compression = 'bz2')

    def load_files(self):
        self.df = pandas.read_csv(self.savepath, index_col=0, compression = 'bz2', dtype=IMPORT_DIC_BBG)
        last_existing_date = datetime.datetime.strptime(self.df.iloc[-1]['Trade Dt'], '%m/%d/%Y').date()
        start_date = last_existing_date + datetime.timedelta(1)
        end_date = datetime.date.today()
        day_count = (end_date - start_date).days + 1 # to include today
        for single_date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            try:
                single_date_str = single_date.strftime('%Y%m%d')
                copy2(STAGINGPATH+'ICBCSFTP-'+single_date_str, BBGPATH)
                daily = pandas.read_csv(BBGPATH+'ICBCSFTP-'+single_date_str)
                self.df = self.df.append(daily,ignore_index=True)
            except IOError as e:
                pass
        self.df.to_csv(self.savepath, compression = 'bz2')
        pass

