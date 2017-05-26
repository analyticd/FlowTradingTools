"""
Slicing and dicing of trade history data from Front.
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0


Classes:
TradeHistory


Functions:
getPrice()
getDate()
getMaturityDate()
filterLondonBooks()
getYday()
is_int()
makeQuery()
reportMonthlyClient()
"""

import pandas
import datetime
import time
#import blpapiwrapper
import os
import cPickle as pickle
import bz2
from StaticDataImport import MYPATH, TEMPPATH, THPATH, DEFPATH, UATPATH, ccy, countries, bonds, LDNFLOWBOOKS, isinsregs, isins144a, allisins, counterparties

#Define globals
#MYPATH='O:\\Global~2\\Credit~2\\Credit~1\\FlowTr~1\\Tools\\'
YTDPATH = 'Z:\\GlobalMarkets\\Credit Trading\\PROD\\Staging\\'
UKSALES = ['COVINOA','TROSSEW','FOXMARK','OXLEYM','SPACHIH','SCRIVENJ','DRABBLES','OZELN','COXLAUR','OLAWOYIM','STIRLINE','LEAMYT','AYRAPETA','SIRIWAJ','DEBEERJ','HOUSERM','CROFTJIM','BYRNEJUL', 'ZOHIDOVG', 'COLQUHI', 'FOLMOMA', 'FROSTG','GOLDBERS','GUESNETP','HARLINGV','MAGALHAB','RILEYP','TREMOCOA','KHUSSAIE', 'PRESTESJ']
NYSALES = ['WILCOCKT','MURPHYG','OHIGGINJ','MELTONED','BIRKHOLD','LIEBERDE','LOPEZLEY','LOPSROG','RADONJIC','SOARESMA','OWOOKWAK']
ASIASALES = ['CHIAWSH','LICHENC']
ALLSALES = UKSALES + NYSALES + ASIASALES


#def getFXRate(x):
#    try:
#        return ccy.get_value(x[0],str(x[1]))
#    except:
#        return 1



#Load counterparty mapping
#xls=pandas.ExcelFile(DEFPATH+'CounterpartyMapping.xlsx')
#counterparties=(xls.parse('Sheet1',index_col=0))
counterpartyshortnamelist = list((counterparties.drop_duplicates(subset='Counterparty'))['Counterparty'])#change to subset

#Create Bloomberg object
#bbgapi=blpapiwrapper.BLP()
def getPrice(series,offset):
    """
    Function to get last price from Bloomberg
    """
    targetDate=series['DateDT']+pandas.tseries.offsets.BDay(offset)
    #print series['DateDT'],targetDate,series['ISIN']
    loop=True
    while loop:
        try:
            out=float(bbgapi.bdh(series['ISIN']+' Corp','PX_LAST',targetDate,targetDate)['PX_LAST'])
            loop=False
        except:
            print series['DateDT'],series['ISIN'], ' have to offset further than ',str(offset)
            pass
        if not loop:
            break
        targetDate=targetDate+pandas.tseries.offsets.BDay(1)
    return out

#Utility functions
def getDate(d):
    return datetime.datetime.strptime(d,'%Y-%m-%d %H:%M:%S')

def getMaturityDate(d):
    """
    Function to parse maturity date in YYYY-MM-DD format
    """
    try:
        output=datetime.datetime.strptime(d,'%Y-%m-%d')
    except:
        output=datetime.datetime(2049,12,31)
    return output

def getMaturityDateOld(d):
    """
    Function to parse maturity date in MM/DD/YYYY format
    """
    try:
        output=datetime.datetime.strptime(d,'%m/%d/%Y')
    except:
        output=datetime.datetime(2049,12,31)
    return output

def filterLondonBooks(book):
    """
    Returns book in LDNFLOWBOOKS   
    """
    return book in LDNFLOWBOOKS

def getYday():
    """
    Get yesterday's date in datetime.datetime format
    """
    return datetime.datetime.today()-datetime.timedelta(days=1)

def is_int(s):
    """
    Return True of s is integer, and False otherwise.
    """
    try:
        int(s)
        return True
    except ValueError:
        return False

###Main class definition###
class TradeHistory:
    """TradeHistory class : Class to build trade history file 

    Attributes:
    df : pandas.DataFrame containing the trade history data 
    positions : positions of trades 
    ALLSALES : UK + NY sales 
    LDNFLOWBOOKS : London flow books (Imported from StaticDataImport)

    Methods:
    __initOld__ <-- still in use?
    __init__
    fulldataclean
    rebuild_historical_database
    precleanup <--still in use?
    remerge_split_trades <--still in use?
    postcleanup <--still in use?
    build_positions
    build_positionsISINBook <--<--still in use?
    getView
    simpleQuery
    viewOneDayTrades
    advancedQuery
    reportMonthlyVolumeSC
    clientTradingReport
    highSCCheck
    regs144a
    newclients 
    compareUKvsNY
    fillPrices
    """

    def __init__(self,fromInputDataFrame=[],forceRebuild=False):
        """
        Keyword arguments:
        fromInputDataFrame : pandas.DataFrame (defaults to [] if not specified)
        """
        time_start=time.time()
        self.enable_dummy = False
        #if database is empty, rebuild the trade history using self.rebuild_historical_database(). Otherwise, read from existing file
        if len(fromInputDataFrame)==0:
            #savepath=TEMPPATH+'th.bin'
            savepathZ=TEMPPATH+'th.binz'
            if forceRebuild or not(os.path.exists(savepathZ)) or datetime.datetime.fromtimestamp(os.path.getmtime(savepathZ)).date()<datetime.datetime.today().date():
                self.df=self.rebuild_historical_database()
                self.fulldataclean(time_start)
                #with open(savepath, 'wb') as outputfile:
                #    pickle.dump(self, outputfile, pickle.HIGHEST_PROTOCOL)
                with bz2.BZ2File(savepathZ, 'w') as outputfileZ:
                    pickle.dump(self,outputfileZ, pickle.HIGHEST_PROTOCOL)
            else:
                print "Found existing file from today"
                #with open(savepath, 'rb') as inputfile:
                with bz2.BZ2File(savepathZ, 'r') as inputfileZ:
                    tempth = pickle.load(inputfileZ)
                    #tempth=pickle.load(inputfile)
                    self.df=tempth.df
                    self.positions=tempth.positions
                    self.ALLSALES=tempth.ALLSALES
                    self.LDNFLOWBOOKS=tempth.LDNFLOWBOOKS
                    self.counterpartyshortnamelist=tempth.counterpartyshortnamelist
                    self.positionsByISINBook=tempth.positionsByISINBook
                    del tempth
                    print 'Database rebuilt in: '+str(int(time.time()-time_start))+' seconds.'
        else:
            self.df=fromInputDataFrame
            self.enable_dummy = True
            self.fulldataclean(time_start)

    def fulldataclean(self,time_start):
        """Function to cleanse data. Function is called when df is built in __init__.
        """
        #print 'Merging: '+str(int(time.time()-time_start))+' seconds.'
        self.precleanup()
        #print 'precleanup: '+str(int(time.time()-time_start))+' seconds.'
        self.remerge_split_trades()
        #print 'splittrades: '+str(int(time.time()-time_start))+' seconds.'
        self.postcleanup()
        #print 'postcleanup: '+str(int(time.time()-time_start))+' seconds.'
        self.build_positions()
        #print 'Positions built: '+str(int(time.time()-time_start))+' seconds.'
        #self.build_positions_new()
        self.build_positionsISINBook()
        self.counterpartyshortnamelist=counterpartyshortnamelist
        self.ALLSALES=ALLSALES
        self.LDNFLOWBOOKS=LDNFLOWBOOKS
        print 'Database rebuilt in: '+str(int(time.time()-time_start))+' seconds.'

    def rebuild_historical_database(self):
        """Function to rebuild historical database 
        """
        TradeHistoryFile='mc_all_trades_pre_2005_20140123_001.txt'
        #read data frame from trade history file
        TradeHistoryDataFrame=pandas.read_csv(THPATH+TradeHistoryFile,index_col=0,sep=';')
        #Read trade history up to 2014 if OS path exist. Otherise rebuild from 2006 to 2015.
        if os.path.exists(THPATH+'FullHistoryTo2016.csv'):
            TradeHistoryDataFrame=pandas.read_csv(THPATH+'FullHistoryTo2016.csv',index_col=0,sep=';')
        else:
            for i in range(2006,2017):
                TradeHistoryFile='mc_all_trades_'+str(i)+'_20140123_001.txt'
                df=pandas.read_csv(THPATH+TradeHistoryFile,index_col=0,sep=';')
                TradeHistoryDataFrame=TradeHistoryDataFrame.append(df,ignore_index=False,verify_integrity=True)
            TradeHistoryDataFrame.to_csv(THPATH+'FullHistoryTo2016.csv',index_col=0,sep=';')
        TradeHistoryFile='SBL_FO_TradeHistory_'+getYday().strftime('%Y%m%d')+'_001.txt'
        df=pandas.read_csv(YTDPATH+TradeHistoryFile,index_col=0,sep=';')
        TradeHistoryDataFrame=TradeHistoryDataFrame.append(df,ignore_index=False,verify_integrity=True)
        return TradeHistoryDataFrame

    def precleanup(self):
        """Function to pre cleanup the data. <--Still in use?
        """
        self.df.rename(columns={'trdnbr':'FrontID','insid':'FrontName','isin':'ISIN','trade_price':'Price','quantity':'Qty','trade_time':'DateSTR','portfolio':'Book',
        'trade_curr':'CCY','Sales Credit':'SCu','Sales Credit MarkUp':'MKu','Counterparty':'FrontCounterparty','Salesperson':'Sales'},inplace=True)
        self.df['ISIN'].fillna('na',inplace=True)
        self.df = self.df[self.df['ISIN']!='na']
        #Clean counterparties
        self.df = self.df.join(counterparties['Counterparty'],on='FrontCounterparty') # this will inject fake trades if duplicated counterparties.
        self.df['Counterparty'].fillna(self.df['FrontCounterparty'], inplace=True)
        #Clean bond names
        self.df=self.df.join(allisins, on='ISIN')
        #ADDING THE FOLLOWING LINES TO DEAL WITH NEW BONDS
        if self.enable_dummy:
            self.df['Bond'].fillna('DUMMY', inplace=True)
        #Dates
        #self.df['DateDT']=self.df['DateSTR'].apply(getDate)
        self.df['DateDT'] = pandas.to_datetime(self.df['DateSTR'],format='%Y-%m-%d %H:%M:%S')
        dti = pandas.DatetimeIndex(self.df['DateDT'])
        self.df['Year'] = dti.year
        self.df['Month'] = dti.month
        self.df['Date'] = self.df['DateDT'].apply(lambda x:x.strftime('%d/%m/%y'))
        self.df['ISIN'] = self.df['ISIN'].replace(to_replace='XX0245586903', value='XS0245586903')#THIS SOLVES THE CCBNKZP issue.
        #self.df['Year']=self.df['DateDT'].apply(lambda x:x.year)
        #self.df['Month']=self.df['DateDT'].apply(lambda x:x.month)
        pass

    def remerge_split_trades(self):
        """Remerge split trades. <--Still in use?
        """
        #Grouping by isin + date + counterparty on the assumption this will be a unique trade ID
        #Summing quantity and then taking max of sales credits to identify misbooked SC across fund splits.
        self.df['id']=self.df['ISIN']+self.df['DateSTR']+self.df['Counterparty']+self.df['Book']#book avoids some mess-ups (ORIGN)
        #SOLUTION BELOW NOT GOOD AS CAN HAVE 2X SAME TRADE SAME DATE SAME COUNTERPARTY SEE 1157974 AND 1158089
        #self.df=self.df.drop_duplicates()##JUST TO MAKE SURE - HAD A REPCAM BUG ON FRONT ID 1466149 - this was due to a duplicated counterparty
        tmp = self.df[['id','Qty','SCu','MKu']]
        grp = tmp.groupby('id')
        s = grp['Qty'].sum()
        sc = grp['SCu'].max()
        mk = grp['MKu'].max()
        self.df.drop_duplicates(subset='id', inplace=True)#change to subset
        self.df.set_index('id', inplace=True, verify_integrity=True)
        self.df['Qty'] = s
        self.df['SCu'] = sc
        self.df['MKu'] = mk
        pass

    def postcleanup(self):
        """Function to cleanse data after split trades have been remerged. <--Still in use?
        """
        self.df['USDQty']=self.df['Qty']
        nusd=self.df[self.df['CCY']!='USD'][['USDQty','Qty','Year','CCY']].copy()
        #for y in range(2009,2015,1):
        #    for c in ccy.index:
        #        nusd['USDQty'][(nusd['Year']==y) & (nusd['CCY']==c)]=nusd['Qty']/ccy.get_value(c,str(y))#bitwise & - careful! otherwise pandas.np.all(c1,c2,axis=0) works                      
        for y in range(2009,2017,1):
            for c in ccy.index:
                nusd.loc[(nusd['Year']==y) & (nusd['CCY']==c),'USDQty']=nusd['Qty']/ccy.loc[c,str(y)]#bitwise & - careful! otherwise pandas.np.all(c1,c2,axis=0) works                      
        self.df.loc[self.df['CCY']!='USD','USDQty']=nusd['USDQty']
        self.df['MKu'].fillna(0,inplace=True)
        self.df['AbsQty']=self.df['USDQty'].abs()
        self.df['SC']=self.df['SCu']*self.df['AbsQty']/10000.
        self.df['MK']=self.df['MKu']*self.df['AbsQty']/10000.
        self.df['TotalSC']=self.df['SC']+self.df['MK']
        #del self.df['DateSTR']
        #self.df.sort(columns='DateDT',inplace=True)
        self.df.sort_values(by='DateDT',inplace=True)
        self.df.reset_index(inplace=True)
        self.df=self.df.join(bonds['TICKER'], on='Bond')
        self.df=self.df.join(bonds['CNTRY_OF_RISK'], on='Bond')
        self.df=self.df.join(bonds['INDUSTRY_GROUP'], on='Bond')
        #self.df['INDUSTRY_GROUP'][self.df['INDUSTRY_GROUP']!='Sovereign']='Corporate'
        self.df.loc[self.df['INDUSTRY_GROUP']!='Sovereign','INDUSTRY_GROUP']='Corporate'
        self.df.rename(columns={'TICKER':'Issuer','CNTRY_OF_RISK':'Country','INDUSTRY_GROUP':'Industry'},inplace=True)
        self.df=self.df.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')
        self.df['Country'].fillna('na',inplace=True)
        self.df['Region'].fillna('na',inplace=True)
        self.df=self.df[self.df['Book'].apply(filterLondonBooks)]
        pass

    def build_positions_new(self):
        positions = self.df.groupby(['ISIN','Book'],as_index=False)['Qty'].sum()
        positions = positions[(positions['Qty']>1) | (positions['Qty']<-1)]#useful here, filter zero positions and errors on amortized bonds
        positions = positions.join(allisins,on='ISIN')
        positions['Series'] = ''
        positions = positions.loc[positions['Bond'].notnull()].copy()
        for (i,row) in positions.iterrows():
            if row['ISIN'] == bonds.loc[row['Bond'],'REGS']:
                positions.loc[i,'Series'] = 'REGS'
            else:
                positions.loc[i,'Series'] = '144A'
        grp = positions.groupby(['Bond','Series'])
        positions = grp['Qty'].sum().unstack().fillna(0)
        positions['Issuer'] = bonds['TICKER']
        positions['Country'] = bonds['CNTRY_OF_RISK']
        positions['CCY'] = bonds['CRNCY']
        positions['Maturity'] = bonds['MATURITY']
        positions['MaturityDT'] = positions['Maturity'].apply(getMaturityDate)
        positions = positions[positions['MaturityDT']>=datetime.datetime.today()]
        positions = positions.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')
        positions['Country'].fillna('na',inplace=True)
        positions['Region'].fillna('na',inplace=True)
        try:
            #This can fail if you add a new bond and then forget to update the bonduniverse.
            positions['USDQty'] = positions.apply(lambda row:row['Qty']/ccy.loc[row['CCY'],'2017'],axis=1)
        except:
            positions['USDQty'] = 0

        positions['Bond'] = positions.index#needed
        self.positions_new = positions
        pass

    def build_positions(self):
        """Builds trade positions. Function is called when building trade history data in __init__
        """
        #Hard-coded 2017 FX rates
        positions = self.df.groupby(self.df['Bond'])['Qty'].sum()
        positions = pandas.DataFrame(positions)
        #positions=positions[positions['Qty']!=0]#this seems to mess up the risktree build on position refresh
        positions['Issuer'] = bonds['TICKER']
        positions['Country'] = bonds['CNTRY_OF_RISK']
        positions['CCY'] = bonds['CRNCY']
        positions['Maturity'] = bonds['MATURITY']
        positions['MaturityDT'] = positions['Maturity'].apply(getMaturityDate)
        positions = positions[positions['MaturityDT']>=datetime.datetime.today()]
        positions = positions.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')
        #positions['USDQty']=positions['Qty']
        positions['Country'].fillna('na',inplace=True)
        positions['Region'].fillna('na',inplace=True)
        try:
            #This can fail if you add a new bond and then forget to update the bonduniverse.
            positions['USDQty'] = positions.apply(lambda row:row['Qty']/ccy.loc[row['CCY'],'2017'],axis=1)
        except:
            positions['USDQty'] = 0

        positions['Bond'] = positions.index#needed
        self.positions = positions
        #
        positions = self.df.groupby(['ISIN','Book'],as_index=False)['Qty'].sum()
        positions = positions[(positions['Qty']>1) | (positions['Qty']<-1)]#useful here, filter zero positions and errors on amortized bonds
        positions = positions.join(allisins, on='ISIN')
        positions['Series'] = ''
        positions = positions.loc[positions['Bond'].notnull()].copy()
        for (i, row) in positions.iterrows():
            if row['ISIN'] == bonds.loc[row['Bond'], 'REGS']:
                positions.loc[i,'Series'] = 'REGS'
            else:
                positions.loc[i,'Series'] = '144A'
        grp = positions.groupby(['Bond','Series'])
        positions = grp['Qty'].sum().unstack().fillna(0)
        if not 'REGS' in positions.columns:
            positions['REGS'] = 0
        if not '144A' in positions.columns:
            positions['144A'] = 0
        self.positions[['REGS','144A']] = positions[['REGS','144A']]
        pass

    def build_positionsISINBook(self):
        """only launched once to get the start of day risk, which will be used for PnL
        """
        positions = self.df.groupby(['ISIN','Book'],as_index=False)['Qty'].sum()
        positions = positions[(positions['Qty']>1) | (positions['Qty']<-1)]#useful here, filter zero positions and errors on amortized bonds
        positions = positions.join(allisins,on='ISIN')
        positions = positions.join(bonds['TICKER'],on='Bond')
        positions = positions.join(bonds['CNTRY_OF_RISK'],on='Bond')
        positions = positions.join(bonds['CRNCY'],on='Bond')
        positions = positions.join(bonds['MATURITY'],on='Bond')
        positions['MaturityDT']=positions['MATURITY'].apply(getMaturityDate)
        positions=positions[positions['MaturityDT']>=datetime.datetime.today()]
        positions.rename(columns={'Qty':'SOD_Pos','CNTRY_OF_RISK':'Country','TICKER':'Issuer','CRNCY':'CCY'},inplace=True)
        positions = positions.join(countries.set_index('Country code',verify_integrity=True)['Region'],on='Country')
        positions['Country'].fillna('na',inplace=True)
        positions['Region'].fillna('na',inplace=True)
        #positions['ISIN']=positions.index#needed
        positions=positions[['Bond','Book','CCY','ISIN','Issuer','Country', 'Region', 'SOD_Pos']]
        positions=positions[pandas.notnull(positions['Bond'])]#filter for bonds that are not understood
        positions['Key'] = positions['Book']+'-'+positions['ISIN']
        positions['Series'] = ''
        for (i,row) in positions.iterrows():
            if row['ISIN']==bonds.loc[row['Bond'],'REGS']:
                positions.loc[i,'Series'] = 'REGS'
            else:
                positions.loc[i,'Series'] = '144A'
        self.positionsByISINBook = positions
        pass

    def appendToday(self,thToday):
        """
        """
        self.df = self.df[self.df['Date']!=datetime.datetime.today().strftime('%d/%m/%y')]#so can do repetitively
        self.df = self.df.append(thToday.df, ignore_index=True)
        self.df = self.df.reindex()
        self.build_positions()#This will get the live risk
        #self.build_positions_new()
        pass

    def getView(self,subdf,item_type):
        """Prints the last 30 entries. Function is called by simpleQuery.
        """
        subdfview = subdf[['Date','Bond','Qty','Price','Counterparty','Sales','SCu','MKu']].copy()
        subdfview['Qty'] = subdfview['Qty'].apply(lambda y:'{:,.0f}'.format(y))
        if item_type in ['Bond','Counterparty','Sales']:
            del subdfview[item_type]
        print subdfview.tail(30)
        pass

    def simpleQuery(self,item_type,item):
        """Fetches the last 30 trades tor the queried item.

        Keyword arguments:
        item_type : Bond, Counterparty, Sales, Issuer, Country
        item  : bondName, counterpartyName, salesPerson, issuerName, countryName 
        """
        subdf = self.df[self.df[item_type]==item].copy()
        print 'Last 30 trades for '+item+':'
        print ''
        self.getView(subdf,item_type)

    def createOneDayTrades(self,date):
        """View 1 day trade.

        Keyword argument:
        date : query date
        """
        subdf=self.df[self.df['Date']==date]
        subdfview=subdf[['Book','Bond','Qty','Price','Counterparty','Sales','SCu','MKu']].copy()
        #subdfview=subdfview.sort(['Book','Bond'])
        subdfview=subdfview.sort_values(by=['Book','Bond'])
        return subdfview

    def viewOneDayTrades(self,date):
        """View 1 day trade.

        Keyword argument:
        date : query date
        """
        # subdf=self.df[self.df['Date']==date]
        # subdfview=subdf[['Book','Bond','Qty','Price','Counterparty','Sales','SCu','MKu']].copy()
        # #subdfview=subdfview.sort(['Book','Bond'])
        # subdfview=subdfview.sort_values(by=['Book','Bond'])
        # subdfview['Qty']=subdfview['Qty'].apply(lambda y:'{:,.0f}'.format(y))
        subdfview = self.createOneDayTrades(date)
        subdfview['Qty']=subdfview['Qty'].apply(lambda y:'{:,.0f}'.format(y))
        print 'Trades for ' + date
        print ''
        print subdfview
        pass

    def advancedQuery(self,item_type,item,startdate,enddate):
        """Advanced query. Prints date, quantity, price, counterparty, sales, SCu, and MKu for queried bond from startdate to enddate

        Keyword arguments:
        item_type : Counterparty/ Sales
        item : name of bond 
        startdate : query start date 
        enddate : query end date 
        """
        subdf=self.df[self.df[item_type]==item].copy()
        #print subdf.shape
        subdf=subdf[subdf['DateDT']>=startdate].copy()
        #print subdf.shape
        subdf=subdf[subdf['DateDT']<=enddate].copy()
        #print subdf.shape
        subdfview=subdf[['Date','Bond','Qty','Price','Counterparty','Sales','SCu','MKu']].copy()
        subdfview['Qty']=subdfview['Qty'].apply(lambda y:'{:,.0f}'.format(y))
        if item_type in ['Bond','Counterparty','Sales']:
            del subdfview[item_type]
        print 'Trades for '+item+' between '+startdate.strftime('%d/%m/%y')+' and '+enddate.strftime('%d/%m/%y')+':'
        print ''
        print subdfview

    def reportMonthlyVolumeSC(self,item_type,item):
        """Query monthly volume and SC

        Keyword arguments:
        item_type : Bond, Client, Salesperson, Issuer, Country, 
        item : bond name
        """
        print 'Volume and SC report for '+item_type+' '+item+':'
        print ''
        subdf=self.df[self.df[item_type]==item].copy()
        print 'Yearly'
        grp=subdf.groupby(['Year'])
        print grp[['AbsQty','SC','MK']].sum().applymap(lambda y:'{:,.0f}'.format(y))
        print ''
        print ''
        print 'Monthly since 2013'
        subsubdf=subdf[subdf['Year']>=2013]
        grp=subsubdf.groupby(['Year','Month'])
        print grp[['AbsQty','SC','MK']].sum().applymap(lambda y:'{:,.0f}'.format(y))
        pass

    def clientTradingReport(self,year,month,book='ALL'):
        """Query client trading report

        keyword arguments:
        year : year 
        month : month 
        book : book (set to all by default.)
        """
        subdf=self.df[self.df['Year']==year]
        if month!=0:
            subdf=subdf[subdf['Month']==month]
        if book!='ALL':
            subdf=subdf[subdf['Book']==book]
        subdf=subdf.copy() # to not have a view anymore
        subdf['NbTrades']=1
        #subdf['TotalSC']=subdf['SC']+subdf['MK']
        #Rank sales
        print ''
        print 'Salesperson analysis'
        grpsales=subdf.groupby('Sales')
        grpsalesview=grpsales[['NbTrades','AbsQty','SC','MK','TotalSC']].sum()
        #grpsalesview=grpsalesview.sort(columns='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        grpsalesview=grpsalesview.sort_values(by='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        print grpsalesview
        print ''
        #Rank clients
        print 'Top 10 clients, by TotalSC'
        grpclients=subdf.groupby('Counterparty')
        grpclientsview=grpclients[['NbTrades','AbsQty','SC','MK','TotalSC']].sum()
        #grpclientsview=grpclientsview.sort(columns='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        grpclientsview=grpclientsview.sort_values(by='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        print grpclientsview.head(20)
        print ''
        #Rank countries
        print 'Country analysis, by TotalSC'
        grpcntry=subdf.groupby('Country')
        grpcntryview=grpcntry[['NbTrades','AbsQty','SC','MK','TotalSC']].sum()
        #grpcntryview=grpcntryview.sort(columns='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        grpcntryview=grpcntryview.sort_values(by='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        print grpcntryview.head(20)
        print ''
        #Rank issuers
        print 'Issuer analysis, by TotalSC'
        grpissuer=subdf.groupby('Issuer')
        grpissuerview=grpissuer[['NbTrades','AbsQty','SC','MK','TotalSC']].sum()
        #grpissuerview=grpissuerview.sort(columns='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        grpissuerview=grpissuerview.sort_values(by='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        print grpissuerview.head(20)
        print ''
        #Rank industry type
        print 'Industry analysis, by TotalSC'
        grpissuer=subdf.groupby('Industry')
        grpissuerview=grpissuer[['NbTrades','AbsQty','SC','MK','TotalSC']].sum()
        #grpissuerview=grpissuerview.sort(columns='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        grpissuerview=grpissuerview.sort_values(by='TotalSC',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        print grpissuerview.head(20)
        print ''
        pass

    def highSCCheck(self,year,month,limit):
        """Query list of high SC Trades

        Keyword arguments: 
        year : year 
        month : month 
        limit : cut off
        """
        subdf=self.df[self.df['Year']==year]
        if month!=0:
            subdf=subdf[subdf['Month']==month]
        subdf['highSC']=(subdf['SCu']>=limit)*1
        subdf['highMK']=(subdf['MKu']>=limit)*1
        subdf['NbTrades']=1
        #subdf['TotalSC']=subdf['SC']+subdf['MK']
        subdf1=subdf[subdf['highSC']!=0]
        subdf2=subdf[subdf['highMK']!=0]
        print ''
        print 'List of high SC trades'
        print subdf1[['Bond','Date','Qty','SCu','MKu','Counterparty','Sales']]
        print ''
        print 'List of high MK trades'
        print subdf2[['Bond','Date','Qty','SCu','MKu','Counterparty','Sales']]
        pass

    def regs144a(self):
        """Query regs144a report 
        """
        positions=self.df.groupby([self.df['Bond'],self.df['ISIN']])['Qty'].sum()
        positions=positions[positions!=0]
        bondindex=positions.index.levels[0]
        for bd in bondindex:
            if positions[bd].shape[0]!=2:#just one position. Careful there are empty positions too
                continue
            i0=positions[bd].index[0]
            i1=positions[bd].index[1]
            p0=positions[bd][0]
            p1=positions[bd][1]
            if (p0<0 and p1<0) or (p0>0 and p1>0):#both positions same sign
                continue
            if p0<0:
                buyisin,buyposition,sellisin,sellposition=i0,p0,i1,p1
            else:
                buyisin,buyposition,sellisin,sellposition=i1,p1,i0,p0
            tradesize=min(sellposition,-buyposition)
            print bd + ': sell '+'{:,.0f}'.format(tradesize)+' of '+sellisin+' to buy '+buyisin
        pass

    def newclients(self,year):
        """Query list of new clients 

        keyword arguments:
        year : year 
        """
        subdf=self.df[self.df['Year']==year].copy()
        subdf=subdf[subdf['FrontCounterparty']==subdf['Counterparty']][['FrontCounterparty', 'Bond', 'Date']]
        subdf=subdf.drop_duplicates()
        subdf['FrontCounterparty']=subdf['FrontCounterparty'].apply(lambda x:pandas.np.nan if ('INTERNAL' in x) else x)
        subdf.dropna(inplace=True)
        print subdf
        pass

    def keyMetricsReport(self,startdate,enddate):
        subdf = self.df[(self.df['DateDT']>=startdate) & (self.df['DateDT']<=enddate)]
        subdf = subdf[['Book','Issuer','Region','AbsQty','SC','MK','TotalSC']].copy()
        subdf['AbsQtyClient'] = 0
        subdf['AbsQtyClient'] = subdf.loc[subdf['TotalSC']!=0,'AbsQty']
        subdf['AbsQtyEM'] = 0
        subdf['AbsQtyEM'] = subdf.loc[~subdf['Issuer'].isin(['T','DBR','UKT', 'OBL']),'AbsQty']
        subdf['AbsQtyMK'] = 0
        subdf['AbsQtyMK'] = subdf.loc[subdf['MK']!=0,'AbsQty']
        book = subdf.groupby('Book')
        region = subdf.groupby('Region')
        return (book.sum(), region.sum())

    def compareUKvsNY(self):
        """Compare client profitabiltiy between UK and NY (called by makeQuery)
        """
        subdf=self.df[self.df['Year']>=2012].copy()
        subdf['NbTrades']=1
        subdf.dropna(subset=['Sales'],inplace=True)
        subdf['NY']=subdf['Sales'].apply(lambda x:x in NYSALES)
        subdf['UK']=subdf['Sales'].apply(lambda x:x in UKSALES)
        subdfNY=subdf[subdf['NY']].copy()
        subdfUK=subdf[subdf['UK']].copy()
        print ''
        print 'Geographical analysis'
        print ''
        print 'New York'
        print '========'
        grpNY=subdfNY.groupby(['Year','Month'])
        print grpNY[['NbTrades','AbsQty','SC','MK','TotalSC']].sum().applymap(lambda y:'{:,.0f}'.format(y))
        print ''
        print 'London'
        print '======'
        grpUK=subdfUK.groupby(['Year','Month'])
        print grpUK[['NbTrades','AbsQty','SC','MK','TotalSC']].sum().applymap(lambda y:'{:,.0f}'.format(y))
        print ''

    def fillPrices(self,year):
        """Fills prices
        """
        subdf=self.df[self.df['Year']==year]
        subdf=subdf[subdf['Bond'].notnull()]#get read of equities etc.
        subdf=subdf[subdf['AbsQty']>=500000].copy()
        self.df['Price1D'][self.df['Year']==year]=subdf.apply(lambda x:getPrice(x,1),axis=1)
        self.df['Price1W'][self.df['Year']==year]=subdf.apply(lambda x:getPrice(x,5),axis=1)
        self.df['PnL1D'][self.df['Year']==year]=(self.df['Price1D']-self.df['Price'])*self.df['Qty']/100.
        self.df['PnL1W'][self.df['Year']==year]=self.df['Price1W']-self.df['Price']*self.df['Qty']/100.

    def checkClientProfitability(self,year):
        """Check client profitabiltiy (called by makeQuery)
        """
        self.df['Price1D']=0.0
        self.df['Price1W']=0.0
        self.df['PnL1D']=0.0
        self.df['PnL1W']=0.0
        for i in range(year,self.df['Year'].max()+1):
            self.fillPrices(i)        
        grp=self.df.groupby(['Year','Client'])
        grppview=grp['PnL1D','Pnl1W'].sum()
        #grpview=grpview.sort(columns='PnL1D',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        grpview=grpview.sort_values(by='PnL1D',ascending=False).applymap(lambda y:'{:,.0f}'.format(y))
        print grpview
        print ''


def makeQuery():
    """
    Not sure if this function is still currently being used...

    """
    error=False
    print 'Please select one of the following:'
    print '1  Query by bond'
    print '2  Query by client'
    print '3  Query by salesperson'
    print '4  Query by issuer'
    print '5  Query by country'
    print '6  Client trading report'
    print '7  High SC check'
    print '8  Rebuild database'
    print '9  New client report'
    print '10 REGS / 144A report'
    print '11 Check profitability report'
    print '12 Compare NY vs. UK'
    print '(Q)uit'
    choiceL1=raw_input('Type number or input bond name or salesperson name:')
    if is_int(choiceL1):
        choiceL1=int(choiceL1)
    ############ BOND REPORTS ############
    if choiceL1==1 or choiceL1 in bonds.index:
        if choiceL1==1:
            bondname=raw_input('Bond name?')
            if not (bondname in bonds.index):
                print 'Bond cannot be found. Back to main menu.'
                error=True
        else:
            bondname=choiceL1.upper()
        if not error:
            print 'Current position: {:,.0f}'.format(th.positions.loc[bondname,'Qty'])
            print ''
            th.simpleQuery('Bond',bondname)
    ############ CLIENT REPORTS ############
    if choiceL1==2:
        clientnameFL=raw_input('Client name search string?')
        matching=[s for s in counterpartyshortnamelist if clientnameFL.lower() in s.lower()]
        if len(matching)==0:
            print 'Client cannot be found. Back to main menu.'
            error=True
        elif len(matching)==1:
            clientname=matching[0]
        else:
            for i,client in enumerate(matching):print str(i)+": "+client
            choiceL2=input('Your choice? ')
            clientname=matching[choiceL2]
        if not error:
            th.simpleQuery('Counterparty',clientname)
    ############ SALESPERSON REPORTS ############
    if choiceL1==3 or choiceL1 in ALLSALES:
        if choiceL1==3:
            for i,sales in enumerate(ALLSALES):print str(i)+": "+sales
            choiceL2=input('Your choice? ')
            sales=ALLSALES[choiceL2]
        else:
            sales=choiceL1.upper()
        th.simpleQuery('Sales',sales)
    ############ ISSUER REPORTS ############
    if choiceL1==4:
        issuername=raw_input('Type Bloomberg ticker of issuer:')
        issuername=issuername.upper()
        if not issuername in list(bonds['TICKER']):
            print 'Issuer cannot be found. Back to main menu.'
            error=True
        if not error:
            th.simpleQuery('Issuer',issuername)
    ############ COUNTRY REPORTS ############
    if choiceL1==5:
        countrycode=raw_input('Type Bloomberg country code:')
        countrycode=countrycode.upper()
        if not countrycode in list(bonds['CNTRY_OF_RISK']):
            print 'Country cannot be found. Back to main menu.'
            error=True
        if not error:
            th.simpleQuery('Country',countrycode)
    ############ CLIENT TRADING REPORTS ############
    if choiceL1==6:
        year=input('Year?')
        month=input('Month, or 0 for full year?')
        th.clientTradingReport(year,month)
    ############ WRONG SC REPORTS ############
    if choiceL1==7:
        year=input('Year?')
        month=input('Month, or 0 for full year?')
        limit=input('Show all trades at or above (c):')
        th.highSCCheck(year,month,limit)
    ############ REBUILD DATABASE ############
    if choiceL1==8:
        th.__init__()
    ############ CHECK NEW CLIENTS ############
    if choiceL1==9:
        year=input('Year?')
        th.newclients(year)
    ############ REGS/144A REPORT ############
    if choiceL1==10:
        th.regs144a()
    ############ CLIENT PROFITABILITY REPORT ############
    if choiceL1==11:
        year=input('Start year?')
        th.checkClientProfitability(year)
    ############ CLIENT PROFITABILITY REPORT ############
    if choiceL1==12:
        th.compareUKvsNY()
    ############ QUIT ############
    if choiceL1=='':
        makeQuery()
    ############ QUIT ############
    if choiceL1=='Q' or choiceL1=='q':
        return
    x=raw_input("Press Enter to continue...")
    makeQuery()
    pass

def reportMonthlyClient():
    pass

def main():
    global th,df14,df15,df16
    print ''
    print 'Rebuilding database, please wait...'
    th=TradeHistory()
    df14=th.df[th.df['Year']==2014]
    df15=th.df[th.df['Year']==2015]
    df16=th.df[th.df['Year']==2016]
    print 'Database name: th, 2014 dataframe name: df14, 2015 dataframe name: df15, 2016 dataframe name: df16'
    print ''
    makeQuery()

if __name__ == '__main__':
    main()
