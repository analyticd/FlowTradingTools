"""
Connect to Front database through COM interface
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0
"""

import win32com.client
import pandas
import pythoncom
import datetime
import time
import TradeHistoryAnalysis
import gc
import sys

from StaticDataImport import bonds, TEMPPATH, allisins, isinsregs, isins144a, LDNFLOWBOOKS

class FrontConnection():
    """
    FrontConnection class: Class to connect to FRONT and download data.


    Methods:
    __init__()
    load_book()
    view_book()
    load_instrument()
    sql_query()
    trade_query()
    historical_price_query()
    closing_price_query()
    new_trades()
    open_repos()
    new_trades_to_csv()
    open_repos_to_csv()
    disconnect()
    """
    def __init__(self,username,password):
        """Keyword arguments:
        username : username
        password : password 
        """
        self.xlApp = win32com.client.Dispatch('aelWrapper.aelConnection')#,clsctx)
        self.xlApp.LoadConfigs('\\\\fotfile01live\\fot_live\\sbl_home\\ini\\vendor\\frontarena\\Prime\\sbl_arena.ini')
        self.environment = 'prime_live'
        self.connected = False
        iRetVal = 0
        counter = 0
        while counter<5:
            iRetVal = self.xlApp.ConnectEx(self.environment, username, password)
            if iRetVal == 1:
                print 'Connection to Front established.'
                self.connected = True
                self.refreshed = True
                break
            else:
                time.sleep(1)
                counter = counter+1
        if iRetVal != 1:
            print 'Failed to connect to Front.'

    def refresh(self):
        self.xlApp.PollADS()
        time.sleep(0.5)
        self.xlApp.PollADS()
        self.refreshed = True

    def load_book(self, bookname, date='2014-10-02'):
        """
        Function to load bond's position, PriceY, and PriceT from FRONT. Function is called by FrontPnL > getBookPnL() 
        Keyword arguments:
        bookname : LDNFLOWBOOKS
        date : defaults to 2014-10-02 unless specified
        """
        oPriceList = win32com.client.Dispatch("aelWrapper.priceList")
        pairs = pandas.np.array([[bookname,'Portfolio']])
        resultSet = oPriceList.GetPriceList(pairs,date,'mktSBLCls')
        bonds = resultSet[0][1]
        isins = list()
        positionsizes = list()
        positionpricesT = list()
        positionpricesY = list()
        for x in bonds:
            isins.append(x[1])
            positionsizes.append(x[4])
            positionpricesT.append((x[8]+x[9])/2)
            positionpricesY.append((x[10]+x[11])/2)
        df = pandas.DataFrame(data={'ISIN':isins,'Position':positionsizes,'PriceT':positionpricesT,'PriceY':positionpricesY})
        df = df.join(allisins,on='ISIN')
        df['Bond'].fillna(df['ISIN'],inplace=True)
        df = df[['Bond','ISIN','Position','PriceY','PriceT']]
        return df

    def view_book(self,bookname,date='2014-10-02'):
        """
        Function to view book's position

        Keyword arguments:
        bookname : LDNFLOWBOOKS
        date : defaults to 2014-10-02 unless specified 
        """
        df = self.load_book(bookname,date)
        del df['Price']
        df = df[abs(df['Position'])>=1.0]
        out = df.groupby('Bond')
        out = out['Position'].sum()
        #out.set_index('Bond',inplace=True,verify_integrity=True)
        out = out.apply(lambda y:'{:,.0f}'.format(y))
        return out

    def load_instrument(self,instrumentname,date):
        """
        Function to load price list and instruments from Front 

        Keyword arguments:
        instrumentname : name of instrument
        date : date 
        """
        oPriceList = win32com.client.Dispatch("aelWrapper.priceList")
        pairs = pandas.np.array([[instrumentname,'Instrument']])
        resultSet = oPriceList.GetPriceList(pairs,date,'mktSBLCls')
        ins = resultSet[0][1][0]
        output = pandas.Series(index=['insid','isin','position','price','priceYday'],data=[ins[0],ins[1],ins[4],0.5*(ins[8]+ins[9]),0.5*(ins[10]+ins[11])])
        return output

    def sql_query(self, asqlstring):
        """
        Function to execute SQL statements  
        keyword argument:
        asqlstring : sql statement
        """
        self.oSQLQuery = win32com.client.Dispatch("aelWrapper.runASQL")
        res = self.oSQLQuery.RunASQL(asqlstring)
        del self.oSQLQuery#release COM object, though unclear it does anything
        self.refreshed = False
        return res

    def trade_query(self, frontID):
        """
        Function to query trade data from Front 

        Keyword arguement:
        frontID : Front ID 
        """
        strFrontID = str(frontID)
        selectString = "t.trdnbr, i.insid, i.isin, t.price, sum(t.quantity*i.contr_size), t.time, t.status, ut.userid, cp.ptyid, display_id(t,'sales_person_usrnbr'), t.sales_credit, add_info(t,'Sales Credit MarkUp')"
        fromString = "instrument i, trade t, user ut, party cp"
        whereString = "i.insaddr=t.insaddr and t.counterparty_ptynbr*=cp.ptynbr and t.trader_usrnbr*=ut.usrnbr"
        res=self.sql_query('select ' + selectString + ' from ' + fromString + ' where t.trdnbr=' + strFrontID + ' and ' + whereString)
        output=pandas.Series(index=['trdnbr','insid','isin','price','quantity','time','status','Trader','FrontCounterparty','Sales','SCu','MKu'],data=res[0])
        if output['SCu'] == '':
            output['SCu'] = '0'
        if output['MKu'] == '':
            output['MKu'] = '0'
        output['trdnbr'] = int(output['trdnbr'])
        output[['price','quantity','SCu','MKu']] = output[['price','quantity','SCu','MKu']].astype(float)
        output['time'] = datetime.date.fromtimestamp(int(output['time']))##
        return output

    def historical_price_query(self, isin='US836205AR58', date='2015-03-31'):
        """
        Funnction to query historical price fron Front. Function is called by FrontPnL > getBookPnL()

        Keyword argument: 
        isin : defaults to SOAF25 US836205AR58
        date : defaults to 2015-03-31 
        """
        #2576 is the code for 'mktSBLCls' 
        #won't work for today
        selectString = "p.bid, p.ask"#, p.last, p.settle"
        fromString = "instrument i, price p, party pt"
        whereString = "i.isin='"+isin+"' and i.insaddr=p.insaddr and p.day='"+date+"' and p.ptynbr=pt.ptynbr and pt.ptynbr=2576"
        res = self.sql_query('select ' + selectString + ' from ' + fromString + ' where ' + whereString)
        if len(res) == 0:
            return 0
        else:
            return 0.5*(float(res[0][0])+float(res[0][1]))        

    def closing_price_query(self,isin='US836205AR58'):
        """
        Function to query closing price from Front. Function is called by FrontPnL > getBookPnL

        keyword argument:
        isin : bond's isin. Defaults to US836205AR58 if not specified.
        """
        selectString="used_price(i,,,'Bid',,'mktSBLCls'), used_price(i,,,'Ask',,'mktSBLCls')"
        fromString="instrument i"
        whereString="i.isin='"+isin+"'"
        res=self.sql_query('select ' + selectString + ' from ' + fromString + ' where ' + whereString)
        return 0.5*(float(res[0][0])+float(res[0][1]))

    def new_trades(self,date='2015-02-23 00:00'):
        """
        Function to load new_trades from Front. Function is called by FrontPnL > getNewTrades (now obsolete?).
        Keyword argument:
        date : defaults to '2015-02-23 00:00' if not specified 
        """
        #if not self.refreshed:
        #    self.refresh()
        self.refresh()
        selectString = "t.trdnbr, i.insid, i.isin, t.price, sum(t.quantity*i.contr_size), t.time, display_id(t,'prfnbr'), display_id(t,'Curr'), t.status, ut.userid, cp.ptyid, display_id(t,'sales_person_usrnbr'), t.sales_credit, add_info(t,'Sales Credit MarkUp')"
        fromString = "instrument i, trade t, user ut, party cp"
        whereString = "i.insaddr=t.insaddr and t.counterparty_ptynbr*=cp.ptynbr and t.trader_usrnbr*=ut.usrnbr and t.status not in ('Void', 'Simulated', 'Valuation') and t.time>='"+date+"'"
        res = self.sql_query('select ' + selectString + ' from ' + fromString + ' where '+ whereString)
        if len(res) == 0: # no new trades yet
            output = pandas.DataFrame(columns=['trdnbr','insid','isin','trade_price','quantity','trade_time','portfolio','trade_curr','status','Trader','Counterparty','Salesperson','Sales Credit','Sales Credit MarkUp'])
        else:
            output = pandas.DataFrame(pandas.np.array(res),columns=['trdnbr','insid','isin','trade_price','quantity','trade_time','portfolio','trade_curr','status','Trader','Counterparty','Salesperson','Sales Credit','Sales Credit MarkUp'])
            output['Sales Credit'].replace('','0',inplace=True)
            output['Sales Credit MarkUp'].replace('','0',inplace=True)
            output['trdnbr'] = output['trdnbr'].astype(int)
            output[['trade_price','quantity','Sales Credit','Sales Credit MarkUp']] = output[['trade_price','quantity','Sales Credit','Sales Credit MarkUp']].astype(float)
            output['trade_time'] = output['trade_time'].apply(lambda x:datetime.datetime.fromtimestamp(int(x)).strftime('%Y-%m-%d %H:%M:%S'))
            output.drop_duplicates(inplace=True)
        return output

    def open_repos(self):
        """
        Function is used to open repos from Front. Function is called by FlowTradingGUI.py > onOpenRepos 
        """
        selectString="t.trdnbr, u.insid, u.isin, i.ref_value*t.quantity, l.fixed_rate"
        fromString="trade t, instrument i, portfolio p, instrument u, leg l"
        whereString="t.prfnbr=p.prfnbr and i.insaddr=t.insaddr and i.instype='Repo/Reverse' and t.status='BO Confirmed' and i.exp_day > YESTERDAY and p.prfid in "+str(tuple(LDNFLOWBOOKS))+" and i.und_insaddr = u.insaddr and l.insaddr = i.insaddr"
        res=self.sql_query('select ' + selectString + ' from ' + fromString + ' where '+ whereString)
        output=pandas.DataFrame(pandas.np.array(res),columns=['trdnbr','insid','ISIN','Quantity','Rate'])
        output['trdnbr']=output['trdnbr'].astype(int)
        output[['Quantity','Rate']]=output[['Quantity','Rate']].astype(float)
        openRepos=output.copy()
        del openRepos['insid']
        isinsregs=pandas.Series(bonds.index,index=bonds['REGS'])
        isins144a=pandas.Series(bonds.index,index=bonds['144A'])
        isinsregs.name='BondREGS'
        isins144a.name='Bond144A'
        isinsregs=isinsregs.drop(isinsregs.index.get_duplicates())
        isins144a=isins144a.drop(isins144a.index.get_duplicates())
        openRepos=openRepos.join(allisins,on='ISIN')
        openRepos=openRepos.join(isinsregs,on='ISIN')
        openRepos=openRepos.join(isins144a,on='ISIN')
        openRepos['Series']=''
        for i in openRepos.index:
            if pandas.isnull(openRepos.loc[i,'BondREGS']):
                openRepos.set_value(i,'Series','144A')
            else:
                openRepos.set_value(i,'Series','REGS')
        openRepos=openRepos[['trdnbr','Bond','Series','ISIN','Quantity','Rate']]
        openRepos.sort_values(by='Bond',inplace=True)
        return openRepos

    def new_trades_to_csv(self,date,savepath):
        """Function to save new_trades to csv 
        """
        output = self.new_trades(date)
        time.sleep(0.5)
        output = self.new_trades(date) # do it a second time to make sure we have a proper refresh
        output.to_csv(TEMPPATH+savepath)
        #MYPATH+'FlowTradingToolsRelease\\newtrades.csv'
        pass

    def open_repos_to_csv(self,savepath):
        """Function to save open repos to csv 
        """
        output=self.open_repos()
        output.to_csv(TEMPPATH+savepath)
        pass

    def disconnect(self):
        """Function to close connection to Front 
        """
        self.xlApp.Disconnect()
        del self.xlApp
        print 'deleted xlApp'
        pythoncom.CoUninitialize()

def main(argv):                         
    if argv[1]=='new_trades':
        fc=FrontConnection(argv[2],argv[3])
        fc.new_trades_to_csv(argv[4],argv[5])
        fc.disconnect()
        del fc
    if argv[1]=='open_repos':
        fc=FrontConnection(argv[2],argv[3])
        fc.open_repos_to_csv(argv[4])
        fc.disconnect()
        del fc        
    gc.collect()
    pass

if __name__ == "__main__":
    main(sys.argv)


