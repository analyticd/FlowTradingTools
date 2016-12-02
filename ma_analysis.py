import pandas
import os
import datetime
import matplotlib
import matplotlib.pyplot as plt
from StaticDataImport import MYPATH, TEMPPATH, THPATH, DEFPATH, UATPATH, ccy, countries, bonds, LDNFLOWBOOKS, isinsregs, isins144a, allisins, MAPATH, counterparties
import blpapiwrapper


BASE_COLUMNS = [u'Status', u'Client', u'Dealer', u'Bid/Offer', u'Issuer', u'Ticker',
u'COUPON', u'Maturity', u'Level', u'Adj. Level', u'Benchmark', u'Price',
u'Cover', u'CUSIP', u'ISIN', u'Inquiry Timestamp', u'Trade DateTime',
u'CLT Trader', u'DLR Trader', u'Settlement Date', u'Inquiry ID',
u'Trade ID', u'LinkID', u'BM CUSIP', u'BM ISIN', u'BM Price', u'Book',
u'Salesperson', u'Yield', u'Z Spread', u'Net Money', u'Sector',
u'Product', u'Protocol', u'Currency', u'Market Category',
u'Inquiry Volume', u'Local Inquiry Volume',
u'Counterparty Response Volume', u'Local Trade Volume']


class FullMarketAxessData():

    def __init__(self, rebuild=False):
        self.savepath = MAPATH+'ma_full.csvz'
        if rebuild:
            self.load_files_full()
        if not(os.path.exists(self.savepath)) or datetime.datetime.fromtimestamp(os.path.getmtime(self.savepath)).date()<datetime.datetime.today().date():
            self.load_files()
        else:
            self.df = pandas.read_csv(self.savepath, parse_dates=['Inquiry Timestamp'], index_col=0, compression='bz2')
        self.df = self.df[['Status','Client','CLT Trader','Bid/Offer','ISIN','Inquiry Timestamp','Currency','Local Inquiry Volume']]
        self.df.rename(columns = {'Local Inquiry Volume':'AbsQty', 'Currency':'CCY','Inquiry Timestamp':'Date'}, inplace = True)
        self.df = self.df[self.df['CCY'].isin(['USD','EUR','CHF','GBP'])]
        self.df = self.df.join(allisins, on = 'ISIN')
        ma_counterparties = counterparties[counterparties['MAName'].notnull()]
        ma_counterparties.set_index('MAName', inplace=True)
        self.df = self.df.join(ma_counterparties['Counterparty'],on='Client')
        self.df = self.df.join(ccy['2016'],on='CCY')
        #self.df['AbsUSDQty'] = self.df.apply(lambda row:row['AbsQty']/ccy.loc[row['CCY'],'2016'],axis=1) ##TOO SLOW
        self.df['AbsUSDQty'] = self.df['AbsQty'] / self.df['2016']
        del self.df['2016']
        self.df['USDQty'] = self.df['AbsUSDQty']
        self.df.loc[self.df['Bid/Offer']=='Offer','USDQty'] = -self.df.loc[self.df['Bid/Offer']=='Offer','USDQty']
        self.df = self.df.join(bonds[['TICKER','CNTRY_OF_RISK']],on='Bond')
        self.df.rename(columns={'TICKER':'Issuer','CNTRY_OF_RISK':'Country'},inplace=True)
        self.df = self.df.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')
        self.df['DateDT'] = self.df['Date']
        #self.df['DateDT'] = pandas.to_datetime(self.df['Date'],format='%d/%m/%Y %H:%M:%S')
        self.df['Date'] = self.df['DateDT'].apply(lambda x:x.date())
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
        self.df = pandas.read_csv(self.savepath, parse_dates=['Inquiry Timestamp'], index_col=0, compression = 'bz2')
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
        dts = dt.strftime('%d/%m/%y')
        subdf=self.df.loc[self.df['Date']==dts]
        grp=subdf.groupby('CCY')
        print grp[['USDQty','AbsQty']].sum().applymap(lambda y:'{:,.2f}'.format(y))
        pass

    def client_report(self, dt):
        dts = dt.strftime('%d/%m/%y')
        subdf = self.df.loc[self.df['Date']==dts]
        grp1 = subdf.groupby('Counterparty')
        sg = grp1.sum()
        out = sg[(sg['USDQty']>=2) | (sg['USDQty']<-2)]
        print out['USDQty'].apply(lambda y:'{:,.1f}'.format(y))
        #print ''
        #grp2=self.df.groupby(['MACounterparty','Country'])
        #print grp2[['USDQty']].sum().applymap(lambda y:'{:,.2f}'.format(y))
        pass

    def region_report(self, dt):
        dts = dt.strftime('%d/%m/%y')
        subdf = self.df.loc[self.df['Date']==dts]
        grp1 = subdf.groupby('Region')
        print grp1[['USDQty']].sum().loc[['Africa','CEE','CIS']].applymap(lambda y:'{:,.1f}'.format(y))
        print ''
        grp2 = self.df.groupby(['Region','Country'])
        print grp2[['USDQty']].sum().loc[['Africa','CEE','CIS']].applymap(lambda y:'{:,.1f}'.format(y))
        pass

    def full_report(self, dt):
        print '=============================================='
        print 'Total enquiries:'
        print '=============================================='
        self.total_report()
        print ''
        print '=============================================='
        print 'Enquiries by region (only accurate for EMEA):'
        print '=============================================='
        self.region_report()
        print ''
        print '=============================================='
        print 'Enquiries by client (showing >$2mm net):'
        print '=============================================='
        self.client_report()
        print ''
        pass



class _deprecated_MAData():
    def __init__(self,filename):
        ma=pandas.read_csv(MAPATH+filename,thousands=',')
        self.df=ma[['Action','Size (000\'s)','Currency','Security','Identifier','Client','Client Trader','Date']].copy()
        self.df.rename(columns={'Size (000\'s)':'AbsQty','Currency':'CCY','Client':'MACounterparty','Identifier':'ISIN'}, inplace = True)
        self.df=self.df[self.df['CCY'].isin(['USD','EUR','CHF','GBP'])]
        self.df['AbsQty']=self.df['AbsQty']/1000.
        self.df['Qty']=self.df['AbsQty']
        self.df.loc[self.df['Action']=='Offer','Qty']=-1*self.df['AbsQty']
        self.df['Qty']=self.df['Qty']
        self.df=self.df.join(allisins,on='ISIN')
        self.df['USDQty']=self.df.apply(lambda row:row['Qty']/ccy.loc[row['CCY'],'2016'],axis=1)
        self.df=self.df.join(bonds[['TICKER','CNTRY_OF_RISK']],on='Bond')
        self.df.rename(columns={'TICKER':'Issuer','CNTRY_OF_RISK':'Country'},inplace=True)
        self.df=self.df.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')
        pass

    def total_report(self):
        grp=self.df.groupby('CCY')
        print grp[['Qty','AbsQty']].sum().applymap(lambda y:'{:,.2f}'.format(y))
        pass

    def client_report(self):
        grp1=self.df.groupby('MACounterparty')
        sg=grp1.sum()
        out=sg[(sg['USDQty']>=2) | (sg['USDQty']<-2)]
        print out['USDQty'].apply(lambda y:'{:,.1f}'.format(y))
        #print ''
        #grp2=self.df.groupby(['MACounterparty','Country'])
        #print grp2[['USDQty']].sum().applymap(lambda y:'{:,.2f}'.format(y))
        pass

    def region_report(self):
        grp1=self.df.groupby('Region')
        print grp1[['USDQty']].sum().loc[['Africa','CEE','CIS']].applymap(lambda y:'{:,.1f}'.format(y))
        print ''
        grp2=self.df.groupby(['Region','Country'])
        print grp2[['USDQty']].sum().loc[['Africa','CEE','CIS']].applymap(lambda y:'{:,.1f}'.format(y))
        pass

    def full_report(self):
        print '=============================================='
        print 'Total enquiries:'
        print '=============================================='
        self.total_report()
        print ''
        print '=============================================='
        print 'Enquiries by region (only accurate for EMEA):'
        print '=============================================='
        self.region_report()
        print ''
        print '=============================================='
        print 'Enquiries by client (showing >$2mm net):'
        print '=============================================='
        self.client_report()
        print ''
        pass

