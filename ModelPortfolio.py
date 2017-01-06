"""
Model portfolio creation and analytics / charting
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2015 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

Functions:
send_mail_via_com()
comptable2013()
maxdrawdown()

Classes:
Display
Builder
PnLBreakdown
Analytics
ModelPortfolio
"""

import win32com.client
import pandas
import datetime
import blpapiwrapper
from math import sqrt
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from StaticDataImport import TEMPPATH, DEFPATH, bonds, BBGHand
BBGHand=' @BVAL'

#Set global variables
BBGAPI=blpapiwrapper.BLP()
TODAY=datetime.datetime.today().replace(hour=0,minute=0,second=0,microsecond=0)
#TODAY=datetime.datetime(2015,8,14)
TMRW=TODAY+datetime.timedelta(days=1)
DAYS2012=pandas.date_range(datetime.datetime(2011,12,31),datetime.datetime(2012,12,31))
DAYS2013=pandas.date_range(datetime.datetime(2012,12,31),datetime.datetime(2013,12,31))
DAYS2014=pandas.date_range(datetime.datetime(2013,12,31),datetime.datetime(2014,12,31))
DAYS2015=pandas.date_range(datetime.datetime(2014,12,31),datetime.datetime(2015,12,31))
DAYS2016=pandas.date_range(datetime.datetime(2015,12,31),datetime.datetime(2016,12,31))
DAYS2017=pandas.date_range(datetime.datetime(2016,12,31),datetime.datetime(2017,12,31))
DAYSFULL=pandas.date_range(datetime.datetime(2011,12,31),datetime.datetime(2017,12,31))
BDAYS2012=pandas.bdate_range(datetime.datetime(2011,12,31),datetime.datetime(2012,12,31))
BDAYS2013=pandas.bdate_range(datetime.datetime(2012,12,31),datetime.datetime(2013,12,31))
BDAYS2014=pandas.bdate_range(datetime.datetime(2013,12,31),datetime.datetime(2014,12,31))
BDAYS2015=pandas.bdate_range(datetime.datetime(2014,12,31),datetime.datetime(2015,12,31))
BDAYS2016=pandas.bdate_range(datetime.datetime(2015,12,31),datetime.datetime(2016,12,31))
BDAYS2017=pandas.bdate_range(datetime.datetime(2016,12,31),datetime.datetime(2017,12,31))
BDAYSFULL=pandas.bdate_range(datetime.datetime(2011,12,31),datetime.datetime(2017,12,31))

#Recreate modelportfolio.py
def send_mail_via_com(text, subject, recipient,a1=False,a2=False):
    """Function to send email to bloomberg when users click on 'send' in the runs menu.
    Function is called by RunsGrid.sendRun()

    Keyword arguments: 
    text : Text message 
    subject : Email subject
    recipient : Recipient of email 
    a1 : attachment (False by default)
    a2 : attachment (False by default)
    """
    #s = win32com.client.Dispatch("Mapi.Session") works for Outlook 2003
    o = win32com.client.Dispatch("Outlook.Application")
    #s.Logon('Outlook') works for Outlook 2003
    #Msg = o.CreateItem(0) works for Outlook 2003
    Msg=o.CreateItem(0x0)#works for Outlook 2007
    Msg.To = recipient
    Msg.Subject = subject
    Msg.Body = text
    if a1<>False:Msg.Attachments.Add(a1)
    if a2<>False:Msg.Attachments.Add(a2)
    Msg.Send()
    pass

def comptable2013():
    """
    Computes return, sharpe ratio, and max drawdawns for the Model porfolio, EMBI, UST10y and ICBCS portfolio vs EMBI
    """
    out=pandas.DataFrame(index=['ModelPortfolio','EMBI','UST10y','ICBCS portfolio vs EMBI'],columns=['Return','Sharpe','MaxDrawdown'])
    out['Return']=bdassets2013.xs(TODAY)-100
    out['Sharpe']=bdasset_sharpe2013
    out['MaxDrawdown']=assets2013.apply(maxdrawdown)
    x=out.transpose()
    x['ICBCS portfolio vs EMBI']=x['ModelPortfolio']-x['EMBI']
    out=out.applymap(lambda u:'{:.1f}'.format(u))
    return out

def maxdrawdown(CumulativePnL):
    """
    Function takes in the cumulative PNL and returns the max drawdown.
    """
    prevmaxi = 0
    prevmini = 0
    maxi = 0
    for i in range(len(CumulativePnL))[1:]:
        if CumulativePnL[i] >= CumulativePnL[maxi]:
            maxi = i
        else:
            # You can only determine the largest drawdown on a downward price!
            if (CumulativePnL[maxi] - CumulativePnL[i]) > (CumulativePnL[prevmaxi] - CumulativePnL[prevmini]):
                prevmaxi = maxi
                prevmini = i
    return -(CumulativePnL[prevmaxi]-CumulativePnL[prevmini])


class Display():

    def __init__(self,modelportfolio):
        self.mp=modelportfolio
        self.txtoutput=self.bbg_txt_output()

    def txt_current_trade(self,bond,period=2014):
        txt='{:<14}'.format(bond)+'{:>6.2f}'.format(self.mp.liveTrades['Price'][bond])+'{:>6.2f}'.format(self.mp.liveTrades['Yield'][bond])+'{:>6.0f}'.format(self.mp.liveTrades['Z-spread'][bond])
        txt+='   '+self.mp.liveTrades['EntryDate'][bond].strftime('%d/%m/%y')+'{:>8.2f}'.format(self.mp.liveTrades['EntryPrice'][bond])
        capitalgain=self.mp.liveTrades['Price'][bond]-self.mp.liveTrades['EntryPrice'][bond]
        carry=(float(self.mp.bonds[bond]['COUPON'])*(TODAY-self.mp.liveTrades['EntryDate'][bond]).days/365)
        if bond=='IVYCST32':
            carry=0
        if period==2013 and self.mp.liveTrades['EntryDate'][bond]<=datetime.datetime(2012,12,31):
            capitalgain=self.mp.liveTrades['Price'][bond]-self.mp.tradedprices[bond][datetime.datetime(2012,12,31)]
            carry=(float(self.mp.bonds[bond]['COUPON'])*(TODAY-datetime.datetime(2012,12,31)).days/365)
        if period==2014 and self.mp.liveTrades['EntryDate'][bond]<=datetime.datetime(2013,12,31):
            capitalgain=self.mp.liveTrades['Price'][bond]-self.mp.tradedprices[bond][datetime.datetime(2013,12,31)]
            carry=(float(self.mp.bonds[bond]['COUPON'])*(TODAY-datetime.datetime(2013,12,31)).days/365)
        if period==2015 and self.mp.liveTrades['EntryDate'][bond]<=datetime.datetime(2014,12,31):
            capitalgain=self.mp.liveTrades['Price'][bond]-self.mp.tradedprices[bond][datetime.datetime(2014,12,31)]
            carry=(float(self.mp.bonds[bond]['COUPON'])*(TODAY-datetime.datetime(2014,12,31)).days/365)
        if period==2016 and self.mp.liveTrades['EntryDate'][bond]<=datetime.datetime(2015,12,31):
            capitalgain=self.mp.liveTrades['Price'][bond]-self.mp.tradedprices[bond][datetime.datetime(2015,12,31)]
            carry=(float(self.mp.bonds[bond]['COUPON'])*(TODAY-datetime.datetime(2015,12,31)).days/365)
        if period==2017 and self.mp.liveTrades['EntryDate'][bond]<=datetime.datetime(2016,12,31):
            capitalgain=self.mp.liveTrades['Price'][bond]-self.mp.tradedprices[bond][datetime.datetime(2016,12,31)]
            carry=(float(self.mp.bonds[bond]['COUPON'])*(TODAY-datetime.datetime(2016,12,31)).days/365)
        if bond=='IVYCST32':
            if period<2013:
                carry=0
            elif period==2013:
                carry=(7.09955*(TODAY-datetime.datetime(2012,12,31)).days/365)
            elif period==2014:
                carry=(7.77433*(TODAY-datetime.datetime(2013,12,31)).days/365)
        if bond == 'FESHRU18' and period >= 2016:
            carry = 0
        txt+='{:>8}'.format('{:>+.2f}'.format(capitalgain))
        txt+='{:>7}'.format('{:>+.2f}'.format(carry))
        txt+='{:>8}'.format('{:>+.2f}'.format(capitalgain+carry))
        return txt

    def bbg_txt_output(self):
        lines=[]
        #Commentary
        lines.append('Performance update:')
        txt='*We are up %.2f%%' %self.mp.performance2017['Returns'].sum() + ' which is %.2f%%' %self.mp.performance2017['CapitalGains'].sum() + ' price appreciation '
        txt+='and %.2f%%' % self.mp.performance2017['Carry'].sum() + ' carry, vs the EMBI which is %.2f%%.' % (self.mp.analytics.assets2017['EMBI'][-1]-100)
        lines.append(txt)
        txt='*Using the 10y note as the risk-free rate, our Sharpe ratio is %.1f' %self.mp.analytics.bdasset_sharpe2017['ModelPortfolio'] + ' vs %.1f' %self.mp.analytics.bdasset_sharpe2017['EMBI'] + ' for the EMBI.'
        lines.append(txt)
        lines.append(' ')
        #Current trades
        lines.append('Full portfolio below:')
        lines.append(' ')
        lines.append('Bond          Price  Yield  Z-spd  Entry     Entry   YTD     YTD     YTD')
        lines.append('                                   date      price   change  carry   P&L')
        lines.append('===========================================================================')
        lines.append('Corporates')
        for bond in self.mp.liveTrades.index:
            if self.mp.bonds[bond]['INDUSTRY_GROUP']=='Sovereign' or self.mp.bonds[bond]['INDUSTRY_GROUP']=='Banks':continue
            lines.append(self.txt_current_trade(bond,2017))
        lines.append(' ')
        lines.append('Banks')
        for bond in self.mp.liveTrades.index:
            if self.mp.bonds[bond]['INDUSTRY_GROUP']<>'Banks':continue
            lines.append(self.txt_current_trade(bond,2017))
        lines.append(' ')
        lines.append('Sovereigns')
        for bond in self.mp.liveTrades.index:
            if self.mp.bonds[bond]['INDUSTRY_GROUP']<>'Sovereign':continue
            lines.append(self.txt_current_trade(bond,2017))
        lines.append('===========================================================================')
        #Old trades
        lines.append('Old trades     Entry       At     Exit       At        Chg    Carry    P&L')
        for trade in self.mp.oldTrades.index:
        #for (i,t) in self.mp.oldTrades.iterrows():
            if self.mp.oldTrades['ExitDate'][trade].year<=2016:
                continue
            bond = self.mp.oldTrades['Bond'][trade]
            entry_ts = self.mp.oldTrades['EntryDate'][trade] 
            exit_ts = self.mp.oldTrades['ExitDate'][trade]
            txt = '{:<15}'.format(bond)
            txt += entry_ts.strftime('%d/%m/%y')
            txt += '  '
            txt += '{:>7.2f}'.format(self.mp.oldTrades['EntryPrice'][trade])
            txt+='  '
            txt+=exit_ts.strftime('%d/%m/%y')
            txt+='  '
            txt+='{:>6.2f}'.format(self.mp.oldTrades['ExitPrice'][trade])
            txt+=' '
            capitalgain=self.mp.capitalgains[bond][max(entry_ts,datetime.datetime(2017,1,1)):exit_ts].sum()
            txt+='{:>8}'.format('{:>+.2f}'.format(capitalgain))
            txt+=' '
            carry=self.mp.bondcarry[bond][max(entry_ts,datetime.datetime(2017,1,1)):exit_ts].sum()
            txt+='{:>6}'.format('{:>+.2f}'.format(carry))
            txt+='  '
            txt+='{:>6}'.format('{:>+.2f}'.format(carry+capitalgain))
            lines.append(txt)
        lines.append('===========================================================================')
        txt='{:<53}'.format('Total')
        txt+='{:>6}'.format('{:>+.2f}'.format(self.mp.performance2017['CapitalGains'].sum()))
        txt+=' '
        txt+='{:>6}'.format('{:>+.2f}'.format(self.mp.performance2017['Carry'].sum()))
        txt+='  '
        txt+='{:>6}'.format('{:>+.2f}'.format(self.mp.performance2017['Returns'].sum()))
        lines.append(txt)
        lines.append(' ')
        #Notes
        #2012: lines.append('Note AZRAIL and ZHAIK adjusted for consent solicitation fees.')
        #2012: lines.append('Ivory Coast adjusted for coupon in the capital gain column.')
        #2013: lines.append('Note Ivory Coast 3Jan13 coupon adjusted for in the capital gain column.')
        #2014: lines.append('Note KKB22 November consent fee adjusted for in the capital gain column.')
        #2015: lines.append('Note Mematu September amortisation P&L adjusted for in the capital gain column.')
        #2016: lines.append('Note Mematu March amortisation P&L adjusted for in the capital gain column.')
        #2016: lines.append('Mematu/Mozam April exchange fee P&L adjusted for in the capital gain column.')
        return lines


class Builder():

    def __init__(self,tradefile):
        self.tradefile=tradefile
        pass

    def load_trades(self):
        trades=pandas.read_csv(DEFPATH+self.tradefile,index_col=0)
        trades['Date']=trades['Date'].apply(lambda x:datetime.datetime.strptime(x,'%d/%m/%Y'))
        return trades

    def load_bonds(self,trades):
        #warning this changes the global variable bonds
        #global bonds
        self.bonds=bonds[['REGS','CRNCY','MATURITY','COUPON','INDUSTRY_GROUP']].copy()
        strbondlist=list(trades.drop_duplicates('Bond')['Bond'])
        self.bonds=self.bonds.reindex(strbondlist)
        self.bonds.rename(columns={'REGS':'ISIN'},inplace=True)
        self.bonds=self.bonds.transpose()
        #bonds['IVYCST32']['COUPON']='7.09955' change
        self.bonds['AFREXI14']['INDUSTRY_GROUP']='Banks'
        self.bonds['PTABNK16']['INDUSTRY_GROUP']='Banks'
        self.bonds['PTABNK18']['INDUSTRY_GROUP']='Banks'
        self.bonds['RCCF16']['INDUSTRY_GROUP']='Banks'
        self.bondcols=self.bonds.columns
        return self.bonds

    def load_historical_bond_prices(self,trades,mp_bonds):
        startdate = trades['Date'].min().to_datetime()
        securities = map(lambda b:bonds.loc[b,'REGS'] + BBGHand + ' Corp',mp_bonds)
        b_to_sec_dic = dict(zip(mp_bonds,securities))
        out = blpapiwrapper.simpleHistoryRequest(securities,['PX_BID','PX_ASK'],startdate,TODAY)
        prices = pandas.DataFrame(index=out.index,columns=mp_bonds)
        for b in mp_bonds:
            prices[b] = 0.5*(out[(b_to_sec_dic[b],'PX_BID')] + out[(b_to_sec_dic[b],'PX_ASK')])
        prices.fillna(method='pad',inplace=True)
        prices = prices.astype('float64')
        prices = prices.reindex(index=DAYSFULL, method='pad')
        return prices

    def load_historical_bond_prices_OLD(self,trades,bonds):
        startdate=trades['Date'].min().to_datetime()
        bondisin=bonds['VIP17']['ISIN']
        out=BBGAPI.bdh(bondisin + BBGHand+' Corp','PX_BID',startdate,TODAY)
        prices=pandas.DataFrame(index=out.index)
        for bond in bonds:
            bondisin=bonds[bond]['ISIN']
            print bond
            #out=BBGAPI.bdh(bondisin + BBGHand+ ' Corp',['PX_BID','PX_ASK'],startdate,TODAY)
            outbid=BBGAPI.bdh(bondisin + BBGHand+ ' Corp',['PX_BID'],startdate,TODAY)
            outask=BBGAPI.bdh(bondisin + BBGHand+ ' Corp',['PX_ASK'],startdate,TODAY)
            outbid.fillna(method='pad',inplace=True)
            outask.fillna(method='pad',inplace=True)
            if bond=='KWIPKK20':
                out=BBGAPI.bdh(bondisin + ' @BGN Corp',['PX_BID','PX_ASK'],startdate,TODAY)
                outbid=out
                outask=out
            #prices[bond]=0.5*(out['PX_BID']+out['PX_ASK'])
            prices[bond]=0.5*(outbid['PX_BID']+outask['PX_ASK'])
        prices.fillna(method='pad',inplace=True)
        prices=prices.astype('float64')
        prices=prices.reindex(index=DAYSFULL, method='pad')
        #print prices.loc[datetime.datetime(2015,9,17)]
        return prices

    def load_bondspecial(self):
        bondspecial=pandas.DataFrame(index=DAYSFULL,columns=self.bondcols)
        bondspecial.fillna(0,inplace=True)
        bondspecial['AZRAIL'][datetime.datetime(2012,2,20)]=0.75
        bondspecial['ZHAIK15'][datetime.datetime(2012,2,20)]=0.5
        bondspecial['IVYCST32'][datetime.datetime(2012,7,4)]=1.875+0.09
        bondspecial['IVYCST32'][datetime.datetime(2013,1,3)]=1.875+0.44927
        bondspecial['KKB22'][datetime.datetime(2014,11,18)]=0.75
        bondspecial['MEMATU'][datetime.datetime(2015,11,9)]=0.09*(100-89)#+(1)*(89-90)#a*(100-Pt) + r*(Pt-Py)
        bondspecial['MEMATU'][datetime.datetime(2016,11,3)]=0.09*(100-81)#+(1-0.09)*(81-80)
        bondspecial['MEMATU'][datetime.datetime(2016,4,6)]=0.359
        return bondspecial

    def load_bondpositions(self,trades,tradedprices):
        bondpositions=pandas.DataFrame(index=DAYSFULL,columns=self.bondcols)
        bondpositions.fillna(0,inplace=True)
        oldTrades=pandas.DataFrame(columns=['Bond','EntryDate','EntryPrice','ExitDate','ExitPrice'])
        liveTrades=pandas.DataFrame(columns=['EntryPrice','EntryDate'])
        for trade in trades.index:
            bond=trades['Bond'].loc[trade]
            bonddate=trades['Date'].loc[trade]
            bondprice=trades['Price'].loc[trade]
            tmrw=bonddate+datetime.timedelta(days=1)
            tradedprices[bond][bonddate]=bondprice
            if trades['Position'].loc[trade]==1:
                liveTrades=liveTrades.append(pandas.DataFrame([[bondprice,bonddate]],index=[bond],columns=['EntryPrice','EntryDate']))
                bondpositions[bond][tmrw:]=1    
            else:
                newrow={'Bond':bond,'EntryDate':liveTrades['EntryDate'][bond],'EntryPrice':liveTrades['EntryPrice'][bond],'ExitDate':bonddate,'ExitPrice':bondprice}
                oldTrades=oldTrades.append(newrow,ignore_index=True)
                liveTrades=liveTrades.drop(bond)
                bondpositions[bond][tmrw:]=0
        for bond in bondpositions:
            bondpositions[bond][TMRW:]=0
        tradedprices.fillna(method='pad',inplace=True)
        return (tradedprices,bondpositions,liveTrades,oldTrades)

    def fill_analytics(self,liveTrades,tradedprices,bonds):
        liveTrades['Price']=0.0
        liveTrades['Yield']=0.0
        liveTrades['Z-spread']=0.0
        liveTrades['Risk']=0.0
        for bond in liveTrades.index:
            #print bond
            liveTrades.loc[bond,'Price']=tradedprices[bond][TODAY]
            liveTrades.loc[bond,'Yield']=BBGAPI.bdp(bonds[bond]['ISIN'] + ' Corp','YLD_YTM_BID','PX_BID',str(liveTrades['Price'][bond]))
            liveTrades.loc[bond,'Z-spread']=BBGAPI.bdp(bonds[bond]['ISIN'] + ' Corp','YAS_ZSPREAD','YAS_BOND_PX',str(liveTrades['Price'][bond]))
            liveTrades.loc[bond,'Risk']=BBGAPI.bdp(bonds[bond]['ISIN'] + ' Corp','RISK_MID')
            if bonds[bond]['ISIN']=='XS0969351450':#MEMATU
                liveTrades.loc[bond,'Z-spread']=BBGAPI.bdp(bonds[bond]['ISIN'] + ' Corp','YAS_ISPREAD','YAS_BOND_PX',str(liveTrades['Price'][bond]))
        liveTrades[['EntryPrice','Price','Yield','Z-spread','Risk']]=liveTrades[['EntryPrice','Price','Yield','Z-spread','Risk']].astype(float)
        return liveTrades

    def build_portfolio(self,bonds,bondpositions,bondspecial,tradedprices):
        #Calculate carry
        bondcarry=pandas.DataFrame(index=DAYSFULL,columns=self.bondcols)
        bondcarry.fillna(0,inplace=True)
        for bond in bonds:
            bondcarry[bond]=float(bonds[bond]['COUPON'])/365
        bondcarry=bondpositions*bondcarry
        for bond in bondcarry:
            bondcarry[bond][datetime.datetime(2011,12,31)]=0
        bondcarry['IVYCST32'][datetime.datetime(2011,12,31):datetime.datetime(2012,12,31)]=0
        bondcarry['IVYCST32'][datetime.datetime(2013,01,01):datetime.datetime(2013,12,31)]=7.09955/365#change
        bondcarry['IVYCST32'][datetime.datetime(2014,01,01):datetime.datetime(2014,12,31)]=7.77433/365#change
        bondcarry['FESHRU18'][datetime.datetime(2015,11,02):datetime.datetime(2015,12,31)]=0#change
        bondcarry['FESHRU18'][datetime.datetime(2016,01,01):datetime.datetime(2016,12,31)]=0#change
        bondcarry['FESHRU18'][datetime.datetime(2017,01,01):datetime.datetime(2017,12,31)]=0#change
        #Calculate capital gains
        capitalgains=bondpositions*(tradedprices-tradedprices.shift(1)+bondspecial)
        capitalgains.fillna(0,inplace=True)
        #Get the full P&L and output
        bondpnl=pandas.DataFrame(index=DAYSFULL,columns=self.bondcols)
        bondpnl.fillna(0,inplace=True)
        bondpnl=capitalgains+bondcarry
        performance=pandas.DataFrame(index=DAYSFULL,columns=['Price','Returns','CapitalGains','Carry'])
        performance['Returns']=bondpnl.sum(axis=1)/20
        performance['CapitalGains']=capitalgains.sum(axis=1)/20
        performance['Carry']=bondcarry.sum(axis=1)/20
        performance['Price']=performance['Returns'].cumsum()+100
        performance['Price'][0]=100
        performancebyyear=performance.groupby(performance.index.year)
        performance2013=performance[performance.index.year>=2013]
        performance2014=performance[performance.index.year>=2014]
        performance2015=performance[performance.index.year>=2015]
        performance2016=performance[performance.index.year>=2016]
        performance2017=performance[performance.index.year>=2017]
        #print 'Return = %.2f%% Capital = %.2f%% Carry = %.2f%%' % (performance['Returns'].sum(), performance['CapitalGains'].sum(), performance['Carry'].sum())
        print performancebyyear.sum()[['Returns','CapitalGains','Carry']]
        return (bondcarry,capitalgains,bondpnl,performance,performance2013,performance2014,performance2015,performance2016,performance2017)


class PnLBreakdown:
    def __init__(self,bondcarry,capitalgains,bondpnl,performance):
        self.bondcarry=bondcarry
        self.capitalgains=capitalgains
        self.bondpnl=bondpnl
        self.performance=performance


class Analytics:
    def __init__(self,performance):
        self.performance=performance
        self.create_comps()

    @staticmethod
    def __build_UST_TR__(isin,startdate,days):
        coupon=float(BBGAPI.bdp(isin,'COUPON'))
        out=BBGAPI.bdh(isin,'PX_LAST',startdate,TODAY)['PX_LAST']
        out=out.reindex(index=days,method='pad')
        outcoupon=pandas.Series(coupon/365,index=days)
        outcoupon[TMRW:]=0
        outcoupon=outcoupon.cumsum()-coupon/365
        out=out+outcoupon
        out=out/out[0]*100
        return out

    @staticmethod
    def __build_EQTY_TR__(bbgcode):
        out=BBGAPI.bdh(bbgcode,'PX_LAST',datetime.datetime(2011,12,15),TODAY)['PX_LAST']
        out=out.reindex(index=DAYSFULL,method='pad')
        out=out/out[0]*100
        return out

    def __reindex_assets__(self,days,ust):
        out=self.assets.reindex(index=days,method='pad')
        out=out/out.ix[0]*100
        del out['UST10y']
        out['UST10y']=ust
        del out['ModelPortfolio']
        out['ModelPortfolio']=self.performance['Price'].reindex(index=DAYSFULL,method='pad')
        out['ModelPortfolio']=out['ModelPortfolio']-out['ModelPortfolio'][0]+100
        out=out.astype(float)
        return out

    def create_comps(self):
        self.assets=pandas.DataFrame(index=DAYSFULL)
        self.assets['ModelPortfolio']=self.performance['Price']
        self.assets['UST10y']=self.__build_UST_TR__('US912828PC88 Corp', datetime.datetime(2011,12,15),DAYSFULL)
        self.assets['EMBI']=self.__build_EQTY_TR__('JPEIGLBL Index')
        self.assets['SPXT']=self.__build_EQTY_TR__('SPXT Index')
        self.assets['USHY']=self.__build_EQTY_TR__('LF98TRUU Index')
        self.assets['XOVER']=self.__build_EQTY_TR__('XTXC GY Equity')
        self.assets=self.assets.astype(float)
        self.assets2013=self.__reindex_assets__(DAYS2013,self.__build_UST_TR__('US912828TY62 Corp', datetime.datetime(2012,12,15),DAYS2013))
        self.assets2014=self.__reindex_assets__(DAYS2014,self.__build_UST_TR__('US912828WE61 Corp', datetime.datetime(2013,12,15),DAYS2014))
        self.assets2015=self.__reindex_assets__(DAYS2015,self.__build_UST_TR__('US912828G385 Corp', datetime.datetime(2014,12,15),DAYS2015))
        self.assets2016=self.__reindex_assets__(DAYS2016,self.__build_UST_TR__('US912828M565 Corp', datetime.datetime(2015,12,15),DAYS2016))
        self.assets2017=self.__reindex_assets__(DAYS2017,self.__build_UST_TR__('US912828U246 Corp', datetime.datetime(2016,12,15),DAYS2017))
        self.bdassets=self.assets.reindex(index=BDAYSFULL)
        self.dbdassets=self.bdassets/self.bdassets.shift(1)-1
        self.bdasset_vol=self.dbdassets[:TODAY].std()*sqrt(260)*100
        self.bdasset_sharpe=(self.bdassets.xs(TODAY)-self.bdassets['UST10y'][TODAY])/self.bdasset_vol
        self.bdassets2013=self.assets2013.reindex(index=BDAYSFULL)
        self.dbdassets2013=self.bdassets2013/self.bdassets2013.shift(1)-1
        self.bdasset_vol2013=self.dbdassets2013[:TODAY].std()*sqrt(260)*100
        self.bdasset_sharpe2013=(self.bdassets2013.xs(TODAY)-self.bdassets2013['UST10y'][TODAY])/self.bdasset_vol2013
        self.bdassets2014=self.assets2014.reindex(index=BDAYSFULL)
        self.dbdassets2014=self.bdassets2014/self.bdassets2014.shift(1)-1
        self.bdasset_vol2014=self.dbdassets2014[:TODAY].std()*sqrt(260)*100
        self.bdasset_sharpe2014=(self.bdassets2014.xs(TODAY)-self.bdassets2014['UST10y'][TODAY])/self.bdasset_vol2014
        self.bdassets2015=self.assets2015.reindex(index=BDAYSFULL)
        self.dbdassets2015=self.bdassets2015/self.bdassets2015.shift(1)-1
        self.bdasset_vol2015=self.dbdassets2015[:TODAY].std()*sqrt(260)*100
        self.bdasset_sharpe2015=(self.bdassets2015.xs(TODAY)-self.bdassets2015['UST10y'][TODAY])/self.bdasset_vol2015
        self.bdassets2016=self.assets2016.reindex(index=BDAYSFULL)
        self.dbdassets2016=self.bdassets2016/self.bdassets2016.shift(1)-1
        self.bdasset_vol2016=self.dbdassets2016[:TODAY].std()*sqrt(260)*100
        self.bdasset_sharpe2016=(self.bdassets2016.xs(TODAY)-self.bdassets2016['UST10y'][TODAY])/self.bdasset_vol2016
        self.bdassets2017=self.assets2017.reindex(index=BDAYSFULL)
        self.dbdassets2017=self.bdassets2017/self.bdassets2017.shift(1)-1
        self.bdasset_vol2017=self.dbdassets2017[:TODAY].std()*sqrt(260)*100
        self.bdasset_sharpe2017=(self.bdassets2017.xs(TODAY)-self.bdassets2017['UST10y'][TODAY])/self.bdasset_vol2017
        pass

class ModelPortfolio():

    def __init__(self,tradefile='modelportfoliotrades.csv'):
        self.builder=Builder(tradefile)
        self.trades=self.builder.load_trades()
        self.bonds=self.builder.load_bonds(self.trades)
        self.tradedprices=self.builder.load_historical_bond_prices(self.trades,self.bonds)
        self.bondspecial=self.builder.load_bondspecial()
        (self.tradedprices,self.bondpositions,self.liveTrades,self.oldTrades)=self.builder.load_bondpositions(self.trades,self.tradedprices)
        (self.bondcarry,self.capitalgains,self.bondpnl,self.performance,self.performance2013,self.performance2014,self.performance2015,self.performance2016,self.performance2017)=self.builder.build_portfolio(self.bonds,self.bondpositions,self.bondspecial,self.tradedprices)
        self.liveTrades=self.builder.fill_analytics(self.liveTrades,self.tradedprices,self.bonds)
        self.analytics=Analytics(self.performance)
        self.display=Display(self)
        pass

    def createoutput(self, mail=False, emailaddress='aalmosni2@bloomberg.net'):
        f=open(TEMPPATH+'txtoutput'+TODAY.strftime('%d%b')+'.txt','w')
        mailbody=''
        for line in self.display.txtoutput:
            f.write('%s\n'%line)
            mailbody=mailbody+line+'\n'
        f.close()
        self.plot_assets(2017,False)
        self.plot_outperformance(2017,False)
        self.plot_full(2017,False)
        if mail:
            send_mail_via_com(mailbody,'Model portfolio performance update',emailaddress,TEMPPATH+'ICBCS-YTD-full'+TODAY.strftime('%d%b')+'.pdf')
        pass

    def dfasset(self,fromyear):
        if fromyear==2012:
            return self.analytics.assets
        elif fromyear==2013:
            return self.analytics.assets2013
        elif fromyear==2014:
            return self.analytics.assets2014
        elif fromyear==2015:
            return self.analytics.assets2015
        elif fromyear==2016:
            return self.analytics.assets2016
        elif fromyear==2017:
            return self.analytics.assets2017

    def plot_assets(self, fromyear=2017, show=True):
        plt.figure()
        ax1=plt.axes()
        out=self.dfasset(fromyear)[:TODAY].copy()
        del out['SPXT']
        del out['USHY']
        del out['XOVER']
        out.plot(ax=ax1,title=str(fromyear)+' asset performance')
        ax1.set_ylabel('Total return')
        ax1.yaxis.grid(color='black', linestyle='dashed')
        plt.savefig(TEMPPATH+'ICBCS-YTD'+TODAY.strftime('%d%b')+'.pdf')
        if show:
            plt.show()
        else:
            plt.close()
        pass

    def plot_outperformance(self, fromyear=2017, show=True):
        plt.figure()
        ax1=plt.axes()
        out=self.dfasset(fromyear)[:TODAY].copy()
        out['ModelPortfolio vs EMBI']=out['ModelPortfolio']-out['EMBI']
        del out['EMBI']
        del out['ModelPortfolio']
        del out['SPXT']
        out['ModelPortfolio vs EMBI'].plot(title='Model portfolio vs EMBI')
        #out['UST10y'].plot(secondary_y=True, style='g')
        ax1.set_ylabel('Total return')
        plt.savefig(TEMPPATH+'ICBCSvsEMBI-YTD'+TODAY.strftime('%d%b')+'.pdf')
        if show:
            plt.show()
        else:
            plt.close()
        pass

    def plot_full(self, fromyear=2017, show=True):
        fig=plt.figure()
        gs = gridspec.GridSpec(2, 1,height_ratios=[2,1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1])
        fig.subplots_adjust(hspace=.25)
        #fig, axes = plt.subplots(nrows=2)
        out=self.dfasset(fromyear)[:TODAY].copy()
        out['ModelPortfolio vs EMBI']=out['ModelPortfolio']-out['EMBI']
        out.rename(columns={'ModelPortfolio':'ICBCS portfolio'},inplace=True)
        out[['ICBCS portfolio','EMBI','UST10y']].plot(ax=ax1)
        ax1.set_title('Total return')
        out['ModelPortfolio vs EMBI'].plot(ax=ax2)
        ax2.set_title('Performance vs EMBI')
        plt.savefig(TEMPPATH+'ICBCS-YTD-full'+TODAY.strftime('%d%b')+'.pdf')
        if show:
            plt.show()
        else:
            plt.close()
        pass

def main():
    global mp
    mp=ModelPortfolio()
    print 'Please select one of the following:'
    print '1 Email to Alex'
    print '2 Pass'
    choice=input('Your choice? ')
    if choice==1:
        mp.createoutput(True,'aalmosni2@bloomberg.net')
    elif choice==2:
        mp.createoutput(True,'')
    else:
        print 'Choice invalid'
    try:x=input('Press Enter to exit')
    except:pass
    pass


if __name__ == '__main__':
    main()


