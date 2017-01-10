"""
Building P&L from Front data
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0


Classes:

DailyPnL
LivePnL

Functions:
getMaturityDate()
"""
import pandas
import FO_Toolkit
import datetime
from StaticDataImport import bonds, TEMPPATH, LDNFLOWBOOKS, countries, ccy, allisins, isinsregs, isins144a
import wx
wxVersion=wx.version()[:3]
if wxVersion=='2.8':
    from wx.lib.pubsub import Publisher as pub
else:
    from wx.lib.pubsub import pub

class MessageContainer():
    def __init__(self,data):
        self.data=data



def getMaturityDate(d):
    """Parse maturity date of bonds in MM/DD/YYYY format    """
    try:
        output=datetime.datetime.strptime(d,'%m/%d/%Y')
    except:
        output=datetime.datetime(2049,12,31)
    return output


class DailyPnL:
    """DailyPnL class: creates a list of PnL items sorted by their individual books. 
    Filters out PnLitems with USD_Total_PnL = 0


    Attributes:
    self.username : FRONT usernamd
    self.password : FRONT password
    self.today : today's date (datetime.datetime object)
    self.yesterday: yesterday's date (datetime.datetime object)
    self.tradeHistory : TradeHistory object, see TradeHistoryAnalysis.TradeHistory (defaults to [] if not specified)
    self.fc : FO_Toolkit.FrontConnection class instance 
    self.pnlitems : DataFrame consisting of all PnL items 
    self.positionDeltas: change in position 
    self.newTrades: New trade information 

    Methods:
    __init__()
    getBookPnL()
    updateNewPrices()
    getNewTrades()
    """

    def __init__(self, username, password, today, yesterday, tradeHistory=[]):
        """Keyword arguments:
        username : FRONT usernamd
        password : FRONT password
        today : today's date (datetime.datetime object)
        yesterday: yesterday's date (datetime.datetime object)
        tradeHistory : TradeHistory object, see TradeHistoryAnalysis.TradeHistory (default to [] if not specified)
        """
        self.front_username=username
        self.front_password=password
        self.today=today
        self.yesterday=yesterday
        self.getNewTrades()
        self.tradeHistory=tradeHistory
        self.fc=FO_Toolkit.FrontConnection(username,password)
        self.pnlitems=pandas.DataFrame(columns=['Key','Book','Bond','CRNCY','Issuer','Region','Country','SOD_Pos','EOD_Pos','dPos','PriceY','PriceT','dP','SOD_PnL','Trade_PnL','Total_PnL','USD_Total_PnL'])
        for book in LDNFLOWBOOKS:
            print 'Loading '+book
            df=self.getBookPnL(book)
            self.pnlitems=self.pnlitems.append(df,ignore_index=True)
        self.pnlitems.to_csv(TEMPPATH+'pnlitems.csv',index=False)

    def getBookPnL(self, book):
        """Function to get PnLitems and calculate PnL for the specified book.

        Keyword argument:
        book : 'APGSG'/'HYCRE'/'KAZAK'/'RUSSI'/'SPCOR'/'SPOT'/'SPTEE'/'TURKE'/'STLBK'
        """
        if self.tradeHistory==[]:
            df = self.fc.load_book(book,self.today)
        else:
            #todaySOD=datetime.datetime.today()
            #todaySOD=datetime.datetime(todaySOD.year,todaySOD.month,todaySOD.day)
            #tdf=self.tradeHistory.df[(self.tradeHistory.df['Book']==book) & (self.tradeHistory.df['DateDT']<todaySOD)]
            #print tdf.shape
            # df = pandas.DataFrame(tdf.groupby('ISIN')['Qty'].sum())
            # df = df[df['Qty']!=0]
            # df['Bond']=allisins
            # df = df.dropna()
            # df = df.join(bonds['MATURITY'], on='Bond')
            # df['MaturityDT']=df['MATURITY'].apply(getMaturityDate)
            # df = df[df['MaturityDT']>=datetime.datetime.today()]
            # df['ISIN'] = df.index
            # df.rename(columns={'Qty':'SOD_Pos'},inplace=True)

            df=self.tradeHistory.positionsByISINBook[self.tradeHistory.positionsByISINBook['Book']==book].copy()            
            df.set_index('ISIN',drop=False,inplace=True)
            df['PriceY'] = 0.0
            df['PriceT'] = 0.0
            df = df[['Bond','ISIN','SOD_Pos','PriceY','PriceT']]
            df['PriceY'] = df['ISIN'].apply(lambda i:self.fc.historical_price_query(i,self.yesterday))
            df['PriceT'] = df['ISIN'].apply(lambda i:self.fc.closing_price_query(i))
        df = df.drop_duplicates('ISIN')#seems some spurious data in STLBK
        #print df
        newTradesB=self.newTrades[self.newTrades['Book']==book].copy()
        newIsins=set(newTradesB['ISIN'])-set(df['ISIN'])
        for i in newIsins:
            #print iz`
            if not i in allisins:
                continue
            row=[allisins[i],i,0,self.fc.historical_price_query(i,self.yesterday),self.fc.closing_price_query(i)]
            rowdf=pandas.DataFrame(data=[row],columns=df.columns)
            df=df.append(rowdf,ignore_index=True)
        df['dP']=df['PriceT']-df['PriceY']
        #Added a try here, because program crashes if newTrades.csv is empty
        try:
            if book in self.positionDeltas.index.get_level_values('Book'): #This line can't execute if newTrades.csv is empty
                df=df.join(self.positionDeltas[book],on='ISIN')
            else:
                df['Qty']=0
        except:
            df['Qty']=0 #Manually create a new column and hack it to 0
        df['Qty'].fillna(0,inplace=True)
        #print df
        df.rename(columns={'Qty':'dPos'},inplace=True)
        if self.tradeHistory==[]:
            df.rename(columns={'Position':'EOD_Pos'},inplace=True)
            df['SOD_Pos']=df['EOD_Pos']-df['dPos']
        else:
            df['EOD_Pos']=df['SOD_Pos']+df['dPos']
        df['SOD_PnL']=df['SOD_Pos']*df['dP']/100.
        df['Book']=book
        df['Key']=df['ISIN'].apply(lambda x:book+'-'+x)            
        df=df.set_index('ISIN', drop=False, verify_integrity=True)
        newTradesB=newTradesB.join(df['PriceT'],on='ISIN')
        newTradesB['TradePnL']=newTradesB['Qty']*(newTradesB['PriceT']-newTradesB['Price'])/100.
        #self.newTradesB=newTradesB
        isinPnL=newTradesB.groupby('ISIN')['TradePnL'].sum()
        df['Trade_PnL']=isinPnL
        df['Trade_PnL'].fillna(0,inplace=True)
        df['Total_PnL']=df['SOD_PnL']+df['Trade_PnL']
        df=df[df['Total_PnL']!=0]
        df=df.join(bonds['CNTRY_OF_RISK'], on='Bond')
        df=df.join(bonds['CRNCY'], on='Bond')
        df=df.join(bonds['TICKER'], on='Bond')
        df=df.join(countries.set_index('Country code'), on='CNTRY_OF_RISK')
        df.rename(columns={'Long name':'Country','TICKER':'Issuer'},inplace=True)
        del df['CNTRY_OF_RISK']
        df['USD_Total_PnL']=df['Total_PnL']
        nusd=df[df['CRNCY']!='USD'][['USD_Total_PnL','Total_PnL','CRNCY']].copy()
        for c in ccy.index:
            i = nusd['CRNCY']==c
            nusd.loc[i,'USD_Total_PnL']=nusd['Total_PnL']/ccy.get_value(c,'2015')
        
        df.loc[df['CRNCY']!='USD','USD_Total_PnL']=nusd['USD_Total_PnL']
        ##HACK - could be pandas bug - https://github.com/pydata/pandas/issues/6322##
        df['Region'].fillna('US',inplace=True)
        df['Country'].fillna('US',inplace=True)
        df['Issuer'].fillna('US',inplace=True)
        ##
        df.sort(['Region','Country','Bond'],inplace=True)
        df=df[['Key','Book','Bond','ISIN','CRNCY','Issuer','Region','Country','SOD_Pos','EOD_Pos','dPos','PriceY','PriceT','dP','SOD_PnL','Trade_PnL','Total_PnL','USD_Total_PnL']]
        return df

    def updateNewPrices(self):
        """Updates new prices by fetching data from FRONT. Function is called when the 'Refresh OED Prices is clicked'
        """
        for i in self.pnlitems.index:
            #trade=self.pnlitems.loc[i]
            if self.pnlitems.loc[i,'PriceT']==0 and self.pnlitems.loc[i,'EOD_Pos']!=0:
                self.pnlitems.loc[i,'PriceT']=self.fc.closing_price_query(self.pnlitems.loc[i,'ISIN'])
                self.pnlitems.loc[i,'dP']=self.pnlitems.loc[i,'PriceT']-self.pnlitems.loc[i,'PriceY']
                self.pnlitems.loc[i,'SOD_PnL']=self.pnlitems.loc[i,'SOD_Pos']*self.pnlitems.loc[i,'dP']/100.
                newTradesBB=self.newTrades[(self.newTrades['Book']==self.pnlitems.loc[i,'Book']) & (self.newTrades['ISIN']==self.pnlitems.loc[i,'ISIN'])].copy()
                if newTradesBB.shape[0]!=0:
                    newTradesBB=newTradesBB.join(self.pnlitems['PriceT'],on='ISIN')
                    newTradesBB['TradePnL']=newTradesBB['Qty']*(newTradesBB['PriceT']-newTradesBB['Price'])/100.
                    self.pnlitems.loc[i,'Trade_PnL']=newTradesBB['TradePnL'].sum()
                self.pnlitems.loc[i,'Total_PnL']=self.pnlitems.loc[i,'SOD_PnL']+self.pnlitems.loc[i,'Trade_PnL']
                print i,self.pnlitems.loc[i,'CRNCY']
                self.pnlitems.loc[i,'USD_Total_PnL']=self.pnlitems.loc[i,'Total_PnL']/ccy.get_value(self.pnlitems.loc[i,'CRNCY'].values[0],'2015')#what's the pb in get value here

    def getNewTrades(self):
        """Pulls any new trades for that day. 
        """
        #We will assume newtrades.csv is already created.
        savepath = 'newtrades.csv'
        #argstring = self.front_username+' '+self.front_password+' '+self.todayDT.strftime('%Y-%m-%d') + ' ' + savepath
        #opstr='python '+MYPATH+'FlowTr~1\\FO_toolkit.py new_trades '+argstring
        #subprocess.call(opstr)
        newTrades=pandas.read_csv(TEMPPATH+savepath)
        newTrades.rename(columns={'trdnbr':'FrontID','insid':'FrontName','isin':'ISIN','trade_price':'Price','quantity':'Qty','trade_time':'DateSTR','portfolio':'Book',
        'trade_curr':'CCY','Sales Credit':'SCu','Sales Credit MarkUp':'MKu','Counterparty':'FrontCounterparty','Salesperson':'Sales'},inplace=True)
        newTrades['ISIN'].fillna('na',inplace=True)
        newTrades=newTrades[newTrades['ISIN']!='na']
        #Clean bond names
        isinsregs=pandas.Series(bonds.index,index=bonds['REGS'])
        isins144a=pandas.Series(bonds.index,index=bonds['144A'])
        isinsregs.name='BondREGS'
        isins144a.name='Bond144A'
        isinsregs=isinsregs.drop(isinsregs.index.get_duplicates())
        isins144a=isins144a.drop(isins144a.index.get_duplicates())
        newTrades=newTrades.join(allisins,on='ISIN')
        newTrades=newTrades.join(isinsregs,on='ISIN')
        newTrades=newTrades.join(isins144a,on='ISIN')
        newTrades['Series']=''
        for i in newTrades.index:
            if pandas.isnull(newTrades.loc[i,'BondREGS']):
                newTrades.set_value(i,'Series','144A')
            else:
                newTrades.set_value(i,'Series','REGS')
        newTrades=newTrades[['FrontID','Bond','Series','ISIN','Qty','Price','Book']]
        newTrades.sort('Bond',inplace=True)
        self.positionDeltas=newTrades.groupby(['Book','ISIN'])['Qty'].sum()
        self.newTrades=newTrades
        pass

class LivePnL:
    """Live class: creates a list of PnLitems sorted by their individual books. Class will update bond analytics 
    whenever there's a BOND_PRICE_UPDATE event, and sends out a message called REFRESH_TREE once the analytics for that
    bond has been updated. 


    Attributes:
    self.username : FRONT usernamd
    self.password : FRONT password
    self.today : today's date (datetime.datetime object)
    self.yesterday: yesterday's date (datetime.datetime object)
    self.tradeHistory : TradeHistory object, see TradeHistoryAnalysis.TradeHistory (defaults to [] if not specified)
    self.fc : FO_Toolkit.FrontConnection class instance 
    self.pnlitems : DataFrame consisting of all PnL items 
    self.positionDeltas: change in position 
    self.newTrades: New trade information 


    Methods:
    __init__()
    getBookPnL()
    updateNewPrices()
    feedLivePrices()
    getNewTrades()
    """
    def __init__(self, username, password, today, yesterday, tradeHistory=[]):
        """Keyword arguments:
        self.username : FRONT usernamd
        self.password : FRONT password
        self.today : today's date (datetime.datetime object)
        self.yesterday: yesterday's date (datetime.datetime object)
        self.tradeHistory : TradeHistory object, see TradeHistoryAnalysis.TradeHistory (default to [] if not specified)
        """
        self.front_username=username
        self.front_password=password
        self.today=today
        self.yesterday=yesterday
        self.getNewTrades()
        self.tradeHistory=tradeHistory
        self.fc=FO_Toolkit.FrontConnection(username,password)
        self.pnlitems=pandas.DataFrame(columns=['Key','Book','Bond','CRNCY','Issuer','Region','Country','SOD_Pos','EOD_Pos','dPos','PriceY','PriceT','dP','SOD_PnL','Trade_PnL','Total_PnL','USD_Total_PnL'])
        for book in LDNFLOWBOOKS:
            print 'Loading '+book
            df=self.getBookPnL(book)
            self.pnlitems=self.pnlitems.append(df,ignore_index=True)
        self.pnlitems.to_csv(TEMPPATH+'pnlitems.csv',index=False)

    def getBookPnL(self, book):
        """Function to get PnLitems and calculate PnL for the specified book.

        Keyword argument:
        book : 'APGSG'/'HYCRE'/'KAZAK'/'RUSSI'/'SPCOR'/'SPOT'/'SPTEE'/'TURKE'/'STLBK'
        """
        if self.tradeHistory==[]:
            df = self.fc.load_book(book,self.today)
        else:
            todaySOD=datetime.datetime.today()
            todaySOD=datetime.datetime(todaySOD.year,todaySOD.month,todaySOD.day)
            tdf=self.tradeHistory.df[(self.tradeHistory.df['Book']==book) & (self.tradeHistory.df['DateDT']<todaySOD)]
            #print tdf.shape
            df = pandas.DataFrame(tdf.groupby('ISIN')['Qty'].sum())
            df = df[df['Qty']!=0]
            df['Bond']=allisins
            df = df.dropna()
            df = df.join(bonds['MATURITY'], on='Bond')
            df['MaturityDT']=df['MATURITY'].apply(getMaturityDate)
            df = df[df['MaturityDT']>=datetime.datetime.today()]
            df['PriceY'] = 0.0
            df['PriceT'] = 0.0
            df['ISIN'] = df.index
            df.rename(columns={'Qty':'SOD_Pos'},inplace=True)
            df = df[['Bond','ISIN','SOD_Pos','PriceY','PriceT']]
            df['PriceY'] = df['ISIN'].apply(lambda i:self.fc.historical_price_query(i,self.yesterday))
            df['PriceT'] = df['ISIN'].apply(lambda i:self.fc.closing_price_query(i))
        df = df.drop_duplicates('ISIN')#seems some spurious data in STLBK
        #print df
        newTradesB=self.newTrades[self.newTrades['Book']==book].copy()
        newIsins=set(newTradesB['ISIN'])-set(df['ISIN'])
        for i in newIsins:
            #print i
            if not i in allisins:
                continue
            row=[allisins[i],i,0,self.fc.historical_price_query(i,self.yesterday),self.fc.closing_price_query(i)]
            rowdf=pandas.DataFrame(data=[row],columns=df.columns)
            df=df.append(rowdf,ignore_index=True)
        df['dP']=df['PriceT']-df['PriceY']
        #Added a try here, because program crashes if newTrades.csv is empty
        try:
            if book in self.positionDeltas.index.get_level_values('Book'): #This line can't execute if newTrades.csv is empty
                df=df.join(self.positionDeltas[book],on='ISIN')
            else:
                df['Qty']=0
        except:
            df['Qty']=0 #Manually create a new column and hack it to 0

        df['Qty'].fillna(0,inplace=True)#fillna = 0 if if-statement executes
            #print df
        df.rename(columns={'Qty':'dPos'},inplace=True)
        if self.tradeHistory==[]:
            df.rename(columns={'Position':'EOD_Pos'},inplace=True)
            df['SOD_Pos']=df['EOD_Pos']-df['dPos']
        else:
            df['EOD_Pos']=df['SOD_Pos']+df['dPos']
        df['SOD_PnL']=df['SOD_Pos']*df['dP']/100.
        df['Book']=book
        df['Key']=df['ISIN'].apply(lambda x:book+'-'+x)            
        df=df.set_index('ISIN', drop=False, verify_integrity=True)
        newTradesB=newTradesB.join(df['PriceT'],on='ISIN')
        newTradesB['TradePnL']=newTradesB['Qty']*(newTradesB['PriceT']-newTradesB['Price'])/100.
        #self.newTradesB=newTradesB
        isinPnL=newTradesB.groupby('ISIN')['TradePnL'].sum()
        df['Trade_PnL']=isinPnL
        df['Trade_PnL'].fillna(0,inplace=True)
        df['Total_PnL']=df['SOD_PnL']+df['Trade_PnL']
        #df=df[df['Total_PnL']!=0] Uncomment this line to show only those bonds with Total_PnL not == 0..
        df=df.join(bonds['CNTRY_OF_RISK'], on='Bond')
        df=df.join(bonds['CRNCY'], on='Bond')
        df=df.join(bonds['TICKER'], on='Bond')
        df=df.join(countries.set_index('Country code'), on='CNTRY_OF_RISK')
        df.rename(columns={'Long name':'Country','TICKER':'Issuer'},inplace=True)
        del df['CNTRY_OF_RISK']
        df['USD_Total_PnL']=df['Total_PnL']
        nusd=df[df['CRNCY']!='USD'][['USD_Total_PnL','Total_PnL','CRNCY']].copy()
        for c in ccy.index:
            i = nusd['CRNCY']==c
            nusd.loc[i,'USD_Total_PnL']=nusd['Total_PnL']/ccy.get_value(c,'2015')
        
        df.loc[df['CRNCY']!='USD','USD_Total_PnL']=nusd['USD_Total_PnL']
        ##HACK - could be pandas bug - https://github.com/pydata/pandas/issues/6322##
        df['Region'].fillna('US',inplace=True)
        df['Country'].fillna('US',inplace=True)
        df['Issuer'].fillna('US',inplace=True)
        ##
        df.sort(['Region','Country','Bond'],inplace=True)
        df=df[['Key','Book','Bond','ISIN','CRNCY','Issuer','Region','Country','SOD_Pos','EOD_Pos','dPos','PriceY','PriceT','dP','SOD_PnL','Trade_PnL','Total_PnL','USD_Total_PnL']]
        return df

    def updateNewPrices(self):
        """Updates the prices to display current live PnL. Function is called when the 'Refresh EOD Prices' button is clicked
        """
        for i in self.pnlitems.index:
            #trade=self.pnlitems.loc[i]
            if self.pnlitems.loc[i,'PriceT']==0 and self.pnlitems.loc[i,'EOD_Pos']!=0: ##I'm not sure why this line is here...
                self.pnlitems.loc[i,'PriceT']=self.fc.closing_price_query(self.pnlitems.loc[i,'ISIN']) ##Uncomment this line if PriceT is only to be loaded by querying closing prices from Front
                self.pnlitems.loc[i,'dP']=self.pnlitems.loc[i,'PriceT']-self.pnlitems.loc[i,'PriceY']
                self.pnlitems.loc[i,'SOD_PnL']=self.pnlitems.loc[i,'SOD_Pos']*self.pnlitems.loc[i,'dP']/100.
                newTradesBB=self.newTrades[(self.newTrades['Book']==self.pnlitems.loc[i,'Book']) & (self.newTrades['ISIN']==self.pnlitems.loc[i,'ISIN'])].copy()
                if newTradesBB.shape[0]!=0:
                    newTradesBB=newTradesBB.join(self.pnlitems['PriceT'],on='ISIN')
                    newTradesBB['TradePnL']=newTradesBB['Qty']*(newTradesBB['PriceT']-newTradesBB['Price'])/100.
                    newTradesBB['TradePnL'].fillna(0,inplace=True)
                    self.pnlitems.loc[i,'Trade_PnL']=newTradesBB['TradePnL'].sum()
                self.pnlitems.loc[i,'Total_PnL']=self.pnlitems.loc[i,'SOD_PnL']+self.pnlitems.loc[i,'Trade_PnL']

                #print i,self.pnlitems.loc[i,'CRNCY']
                self.pnlitems.loc[i,'USD_Total_PnL']=self.pnlitems.loc[i,'Total_PnL']/ccy.get_value(self.pnlitems.loc[i,'CRNCY'].values[0],'2015')#what's the pb in get value here

    def feedLivePrices(self,message):
        """Updates current prices from bloomberg. Function is called by guiWidgets > LivePnLTabPanel.livePrices()
        When a new bond price becomes available, the bond analytics for that bond is updated. Functions then sends out 
        a 'REFRESH_TREE' message to update the Live PnL tree. 

        PnLTreeView.onRefreshTree listens to the REFRESH_TREE event. 
        """
        newPrice=message.data
        bond=newPrice.name
        # Only updates the bond's PriceT if it is in self.pnlitems
        if bond in list(self.pnlitems['Bond']):
            i=self.pnlitems['Bond']==bond
            #Update bond analytics
            self.pnlitems.loc[i,'PriceT']=newPrice['MID'] #PriceT is now the new mid price
            self.pnlitems.loc[i,'dP']=self.pnlitems.loc[i,'PriceT']-self.pnlitems.loc[i,'PriceY']#Get the new dP for the bond
            self.pnlitems.loc[i,'SOD_PnL']=self.pnlitems.loc[i,'SOD_Pos']*self.pnlitems.loc[i,'dP']/100.#SOD_PnL = SOD_pos * dP
            
            ##Get new trades
            #Create a newtradesBB DataFrame
            newtradesBB = pandas.DataFrame(columns=self.newTrades.columns)

            #For each bond, there may be multiplie entries in pnlitems, each with its own 'Book' and 'ISIN', which may be
            #the same or different. Therefore for each line in the pnlitems, we want to grab the items in the newtrades file
            #that corresponds to the same book and isin.
            for m in range(len(self.pnlitems.loc[i,['Book','ISIN']])):
                book = self.pnlitems.loc[i,['Book','ISIN']].values[m][0]
                isin = self.pnlitems.loc[i,['Book','ISIN']].values[m][1]
                #Grab lines in newtrades that has the same 'Book' and 'ISIN' as the pnlitems
                line = self.newTrades[(self.newTrades['Book']==book)&(self.newTrades['ISIN']==isin)]
                if len(line) !=0:#If the line exist in newtrades, we append it to newtradesBB
                    for n in range(len(line)):
                        newtradesBB.loc[len(newtradesBB)]=line.iloc[n]
                        #Grab priceT from pnlitems
                        newtradesBB.loc[len(newtradesBB)-1,'PriceT']=(self.pnlitems[self.pnlitems['ISIN']==isin]['PriceT'].values[0])

            #Calculate the TradePnL for that new trade if it exists.
            if len(newtradesBB)!=0:
                newtradesBB['TradePnL']=newtradesBB['Qty']*(newtradesBB['PriceT']-newtradesBB['Price'])/100.
                newtradesBB['TradePnL'].fillna(0,inplace=True)

            #newtradesBB DataFrame now contains all newtrades fields + PriceT and TradePnL.
            #Now, we need to sum up all the trades for the same bond&isin, then add it to the pnlitems corresponding to the 
            #same book and isin
            for m in range(len(newtradesBB)):
                book = newtradesBB.loc[m,'Book']
                isin = newtradesBB.loc[m,'ISIN']
                newtradesSum=newtradesBB.loc[(newtradesBB['Book']==book)&(newtradesBB['ISIN']==isin),'TradePnL'].sum()
                self.pnlitems.loc[(self.pnlitems['Book']==book)&(self.pnlitems['ISIN']==isin),'Trade_PnL']=newtradesSum


            #Now, compute the Total_PnL and USD_Total_PnL
            self.pnlitems.loc[i,'Total_PnL']=self.pnlitems.loc[i,'SOD_PnL'] + self.pnlitems.loc[i,'Trade_PnL']
            self.pnlitems.loc[i,'USD_Total_PnL'] = self.pnlitems.loc[i,'Total_PnL']/ccy.get_value(self.pnlitems.loc[i,'CRNCY'].values[0],'2015')
            
            #Once all the analytics are updated, send out a 'REFRESH_TREE' event
            if wxVersion=='2.8':
                pub.sendMessage('REFRESH_TREE', self.pnlitems.loc[i])
            else:
                pub.sendMessage('REFRESH_TREE', message=MessageContainer(self.pnlitems.loc[i]))
  
    def getNewTrades(self):
        """Fetches new trade data from newtrades.csv
        """
        #We will assume newtrades.csv is already created.
        savepath = 'newtrades.csv'
        #argstring = self.front_username+' '+self.front_password+' '+self.todayDT.strftime('%Y-%m-%d') + ' ' + savepath
        #opstr='python '+MYPATH+'FlowTr~1\\FO_toolkit.py new_trades '+argstring
        #subprocess.call(opstr)
        newTrades=pandas.read_csv(TEMPPATH+savepath)
        newTrades.rename(columns={'trdnbr':'FrontID','insid':'FrontName','isin':'ISIN','trade_price':'Price','quantity':'Qty','trade_time':'DateSTR','portfolio':'Book',
        'trade_curr':'CCY','Sales Credit':'SCu','Sales Credit MarkUp':'MKu','Counterparty':'FrontCounterparty','Salesperson':'Sales'},inplace=True)
        newTrades['ISIN'].fillna('na',inplace=True)
        newTrades=newTrades[newTrades['ISIN']!='na']
        #Clean bond names
        isinsregs=pandas.Series(bonds.index,index=bonds['REGS'])
        isins144a=pandas.Series(bonds.index,index=bonds['144A'])
        isinsregs.name='BondREGS'
        isins144a.name='Bond144A'
        isinsregs=isinsregs.drop(isinsregs.index.get_duplicates())
        isins144a=isins144a.drop(isins144a.index.get_duplicates())
        newTrades=newTrades.join(allisins,on='ISIN')
        newTrades=newTrades.join(isinsregs,on='ISIN')
        newTrades=newTrades.join(isins144a,on='ISIN')
        newTrades['Series']=''
        for i in newTrades.index:
            if pandas.isnull(newTrades.loc[i,'BondREGS']):
                newTrades.set_value(i,'Series','144A')
            else:
                newTrades.set_value(i,'Series','REGS')
        newTrades=newTrades[['FrontID','Bond','Series','ISIN','Qty','Price','Book']]
        newTrades.sort('Bond',inplace=True)
        self.positionDeltas=newTrades.groupby(['Book','ISIN'])['Qty'].sum()
        self.newTrades=newTrades
        pass

class DailyPnLNew:
    """DailyPnL class: creates a list of PnL items sorted by their individual books. 
    Filters out PnLitems with USD_Total_PnL = 0


    Attributes:
    self.username : FRONT usernamd
    self.password : FRONT password
    self.today : today's date (datetime.datetime object)
    self.yesterday: yesterday's date (datetime.datetime object)
    self.tradeHistory : TradeHistory object, see TradeHistoryAnalysis.TradeHistory (defaults to [] if not specified)
    self.fc : FO_Toolkit.FrontConnection class instance 
    self.pnlitems : DataFrame consisting of all PnL items 
    self.positionDeltas: change in position 
    self.newTrades: New trade information 

    Methods:
    __init__()
    getBookPnL()
    updateNewPrices()
    getNewTrades()
    """

    def __init__(self, tradeHistory, bdm, today, yesterday):
        """Keyword arguments:
        username : FRONT usernamd
        password : FRONT password
        today : today's date (datetime.datetime object)
        yesterday: yesterday's date (datetime.datetime object)
        tradeHistory : TradeHistory object, see TradeHistoryAnalysis.TradeHistory (default to [] if not specified)
        """
        self.today = today
        self.yesterday = yesterday
        self.getNewTrades()
        self.tradeHistory = tradeHistory
        self.bdm = bdm
        self.pnlitems=pandas.DataFrame(columns=['Key','Book','Bond','CRNCY','Issuer','Region','Country','SOD_Pos','EOD_Pos','dPos','PriceY','PriceT','dP','SOD_PnL','Trade_PnL','Total_PnL','USD_Total_PnL'])
        for book in LDNFLOWBOOKS:
            print 'Loading '+book
            if book=='CMNC2':
                continue
            df=self.getBookPnL(book)
            self.pnlitems=self.pnlitems.append(df,ignore_index=True)
        self.pnlitems.set_index('Key',inplace=True)
        self.pnlitems.to_csv(TEMPPATH+'livepnlitems.csv')

    def findPrice(self, row):
        #print row
        try:
            return self.bdm.df.loc[row['Bond'],'MID']
        except:
            return row['PriceY']

    def getBookPnL(self, book):
        """Function to get PnLitems and calculate PnL for the specified book.

        Keyword argument:
        book : 'APGSG'/'HYCRE'/'KAZAK'/'RUSSI'/'SPCOR'/'SPOT'/'SPTEE'/'TURKE'/'STLBK'
        """
        df=self.tradeHistory.positionsByISINBook[self.tradeHistory.positionsByISINBook['Book']==book].copy()
        df.set_index('ISIN', drop=False, inplace=True)
        df['PriceT'] = 0.0
        df = df[['Bond','ISIN','SOD_Pos','PriceY','PriceT']]
        df['PriceT'] = df.apply(self.findPrice, axis=1)
        df = df.drop_duplicates('ISIN')#seems some spurious data in STLBK
        #print df
        newTradesB=self.newTrades[self.newTrades['Book']==book].copy()
        newIsins=set(newTradesB['ISIN'])-set(df['ISIN'])
        for i in newIsins:
            print i
            if not i in allisins:
                continue
            row=[allisins[i],i,0,pandas.np.nan,self.bdm.df.loc[allisins[i],'MID']]
            rowdf=pandas.DataFrame(data=[row],columns=df.columns)
            df=df.append(rowdf,ignore_index=True)
        df['dP']=df['PriceT']-df['PriceY']
        #Added a try here, because program crashes if newTrades.csv is empty
        try:
            if book in self.positionDeltas.index.get_level_values('Book'): #This line can't execute if newTrades.csv is empty
                df=df.join(self.positionDeltas[book],on='ISIN')
            else:
                df['Qty']=0
        except:
            df['Qty']=0 #Manually create a new column and hack it to 0
        df['Qty'].fillna(0,inplace=True)
        #print df
        df.rename(columns={'Qty':'dPos'},inplace=True)
        print df
        df['EOD_Pos']=df['SOD_Pos']+df['dPos']
        df['SOD_PnL']=df['SOD_Pos']*df['dP']/100.
        df['SOD_PnL'].fillna(0, inplace=True)
        df['Book']=book
        df['Key']=df['ISIN'].apply(lambda x:book+'-'+x)            
        df=df.set_index('ISIN', drop=False, verify_integrity=True)
        newTradesB=newTradesB.join(df['PriceT'],on='ISIN')
        newTradesB['TradePnL']=newTradesB['Qty']*(newTradesB['PriceT']-newTradesB['Price'])/100.
        #self.newTradesB=newTradesB
        isinPnL=newTradesB.groupby('ISIN')['TradePnL'].sum()
        df['Trade_PnL']=isinPnL
        df['Trade_PnL'].fillna(0,inplace=True)
        df['Total_PnL']=df['SOD_PnL']+df['Trade_PnL']
        df=df[df['Total_PnL']!=0]
        df=df.join(bonds['CNTRY_OF_RISK'], on='Bond')
        df=df.join(bonds['CRNCY'], on='Bond')
        df=df.join(bonds['TICKER'], on='Bond')
        df=df.join(countries.set_index('Country code'), on='CNTRY_OF_RISK')
        df.rename(columns={'Long name':'Country','TICKER':'Issuer'},inplace=True)
        del df['CNTRY_OF_RISK']
        df['USD_Total_PnL']=df['Total_PnL']
        nusd=df[df['CRNCY']!='USD'][['USD_Total_PnL','Total_PnL','CRNCY']].copy()
        for c in ccy.index:
            i = nusd['CRNCY']==c
            nusd.loc[i,'USD_Total_PnL']=nusd['Total_PnL']/ccy.get_value(c,'2015')
        
        df.loc[df['CRNCY']!='USD','USD_Total_PnL']=nusd['USD_Total_PnL']
        ##HACK - could be pandas bug - https://github.com/pydata/pandas/issues/6322##
        df['Region'].fillna('US',inplace=True)
        df['Country'].fillna('US',inplace=True)
        df['Issuer'].fillna('US',inplace=True)
        ##
        df.sort_values(by=['Region','Country','Bond'],inplace=True)
        df=df[['Key','Book','Bond','ISIN','CRNCY','Issuer','Region','Country','SOD_Pos','EOD_Pos','dPos','PriceY','PriceT','dP','SOD_PnL','Trade_PnL','Total_PnL','USD_Total_PnL']]
        return df

    def updateBondPrice(self,bond,price):
        for book in LDNFLOWBOOKS:
            for isin in [bonds.loc[bond,'REGS'],bonds.loc[bond,'144A']]:
                key=book+'-'+isin
                if key in self.df.index:
                    ddp=price-self.df.loc[key,'PriceT']
                    self.df.loc[key,'SOD_PnL'] = self.df.loc[key,'SOD_Pos'] + self.df.loc[key,'SOD_Pos']*ddp
                    self.df.loc[key,'Trade_PnL'] = self.df.loc[key,'Trade_PnL'] + self.df.loc[key,'dPos']*ddp
                    self.df.loc[key,'Total_PnL'] = self.df.loc[key,'Trade_PnL'] + self.df.loc[key,'SOD_PnL']
                    self.df.loc[key,'USD_Total_PnL'] = self.df.loc[key,'Trade_PnL'] / ccy.get_value(self.df.loc[key,'CRNCY'],'2016')
                    self.df.loc[key,'dP'] = self.df.loc[key,'dP'] + ddp
                    self.df.loc[key,'PriceT'] = price
                    pass
                pass
            pass
        #placeholder - call a refresh tree
        pass

    def getNewTrades(self):
        """Pulls any new trades for that day. 
        """
        #We will assume newtrades.csv is already created.
        savepath = 'newtrades.csv'
        #argstring = self.front_username+' '+self.front_password+' '+self.todayDT.strftime('%Y-%m-%d') + ' ' + savepath
        #opstr='python '+MYPATH+'FlowTr~1\\FO_toolkit.py new_trades '+argstring
        #subprocess.call(opstr)
        newTrades=pandas.read_csv(TEMPPATH+savepath)
        newTrades.rename(columns={'trdnbr':'FrontID','insid':'FrontName','isin':'ISIN','trade_price':'Price','quantity':'Qty','trade_time':'DateSTR','portfolio':'Book',
        'trade_curr':'CCY','Sales Credit':'SCu','Sales Credit MarkUp':'MKu','Counterparty':'FrontCounterparty','Salesperson':'Sales'},inplace=True)
        newTrades['ISIN'].fillna('na',inplace=True)
        newTrades=newTrades[newTrades['ISIN']!='na']
        #Clean bond names
        isinsregs=pandas.Series(bonds.index,index=bonds['REGS'])
        isins144a=pandas.Series(bonds.index,index=bonds['144A'])
        isinsregs.name='BondREGS'
        isins144a.name='Bond144A'
        isinsregs=isinsregs.drop(isinsregs.index.get_duplicates())
        isins144a=isins144a.drop(isins144a.index.get_duplicates())
        newTrades=newTrades.join(allisins,on='ISIN')
        newTrades=newTrades.join(isinsregs,on='ISIN')
        newTrades=newTrades.join(isins144a,on='ISIN')
        newTrades['Series']=''
        for i in newTrades.index:
            if pandas.isnull(newTrades.loc[i,'BondREGS']):
                newTrades.set_value(i,'Series','144A')
            else:
                newTrades.set_value(i,'Series','REGS')
        newTrades=newTrades[['FrontID','Bond','Series','ISIN','Qty','Price','Book']]
        newTrades.sort_values(by='Bond',inplace=True)
        self.positionDeltas=newTrades.groupby(['Book','ISIN'])['Qty'].sum()
        self.newTrades=newTrades
        pass

