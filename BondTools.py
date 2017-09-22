"""
Bond relative value charting tools and maintenance tools
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

Classes:
ChartTypes
ScatterChart 
BarChart
ChartEngine
HistoryRequest

Functions:
refresh_bond_universe()
create_chart_file()
africa_weekly()
"""

import pandas
import blpapiwrapper
import matplotlib
matplotlib.use("WxAgg")
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import datetime
from matplotlib.backends.backend_pdf import PdfPages
from subprocess import Popen
import threading
from StaticDataImport import DEFPATH, TEMPPATH, bonds, SPECIALBONDS, BONDCHARTS, BONDCHARTCOLORS, ratingsScale, logoFile, isinsregs
from matplotlib.image import imread
from scipy.misc import imresize

import ma_analysis

import wx
wxVersion=wx.version()[:3]
from wx.lib.pubsub import pub


#Load logo
logo = imread(DEFPATH+logoFile)
logo = imresize(logo,0.08)


class MessageContainer():
    def __init__(self,data):
        self.data = data

class ChartTypes:
    """ChartTypes class: Class to define chart types 
    """
    SpreadVsDuration, SpreadVsRating, ZScoreVsIndex, YTDRange, YTDPerformance, MAVolume = range(6)

class ScatterChart():
    """ScatterChart class : class to define Scatter chart 

    Attributes:
    self.xdata : x data 
    self.ydata : y data 
    self.fig : plt.figure()
    self.ax : Addes axes at positions ((left, bottom, width, height)). See matplotlib's documentation.
    self.ax2 : Adds existing axes (self.ax) to self.ax2 (see matplotlib's documentation)

    Methods:
    __init__()
    ZSpreadTemplate()
    ZSpreadYTDTemplate()
    ZScoreTemplate()
    RatingTemplate()
    """
    def __init__(self,titlelabel,xlabel,ylabel,xdata,ydata,labels,colors,labeltextsize, PDF):
        """
        Keyword arguments:
        titlelabel : title of plot
        xlabel : x axis label 
        ylabel : y axis label 
        xdata : x data 
        ydata : y data 
        labels : data labels 
        colors : data colours 
        labeltextsize : size of labels 
        """
        self.xdata = xdata
        self.ydata = ydata
        self.fig = plt.figure() if PDF == True else Figure()
        self.ax = self.fig.add_axes((0.1,.15,0.8,.7))
        self.ax.set_title(titlelabel)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.fig.subplots_adjust(bottom = 0.1)
        self.ax.scatter(xdata, ydata, marker = '.', c = colors, s = 100)
        for label, x, y in zip(labels, xdata, ydata):
            self.ax.annotate(label,xy = (x, y), xytext = (0, -10),textcoords = 'offset points', ha = 'center', va = 'center', size=labeltextsize)
        self.ax.grid(b=True,which='major',axis='y',linestyle='--')
        self.fig.text(.4,.05, datetime.datetime.today().strftime('%d%b%Y') + ' Credit Trading desk - all data is indicative.',size=labeltextsize)
        self.fig.figimage(logo,10,0)

    def ZSpreadTemplate(self):
        """
        Function to define the template for ZSpread Charts. Function is called by:
        ZSpreadYTDTemplate, chartEngine.plot_group()
        """
        xmin,xmax = self.ax.get_xlim()
        ymin,ymax = self.ax.get_ylim()
        self.ax.set_xlim((max(0,xmin),xmax))
        self.ax.set_ylim((max(0,ymin),ymax))

    def ZSpreadYTDTemplate(self,lowbar,highbar):
        """Function to define the tempalte for year-to-date ZSpread charts. Function is called by:
        BondTools.plot_group_ytd_spread()

        Keyword arguments:
        lowbar : lower limit of error bar 
        highbar : upper limit of error bar 
        """
        self.ZSpreadTemplate()
        self.ax2 = self.fig.add_axes(self.ax)
        self.ax2.errorbar(self.xdata, self.ydata, [lowbar,highbar], fmt=None, ecolor='black')

    def ZScoreTemplate(self):
        """Function to define the template for ZScore charts. Function is called by:
        ChartEngine.scatter_plot_zscores()
        """
        xmin,xmax = self.ax.get_xlim()
        ymin,ymax = self.ax.get_ylim()
        xn = max(abs(xmin),xmax,2.5)
        self.ax.set_xlim((-xn,xn))
        yn = max(abs(ymin),ymax,2.5)
        self.ax.set_ylim((-yn,yn))
        self.fig.gca().set_aspect('equal', adjustable='box')#plt.axis('equal')
        self.ax.grid(b=True,which='major',axis='y',linestyle='--')
        self.ax.grid(b=True,which='major',axis='x',linestyle='--')
        circle1 = plt.Circle((0,0),1,color='b',fill=False)
        circle2 = plt.Circle((0,0),2,color='r',fill=False)
        self.fig.gca().add_artist(circle1)
        self.fig.gca().add_artist(circle2)

    def RatingTemplate(self):
        """Function to define the template for Rating charts. Function is called by:
        ChartEngine.scatter_plot_zscores()
        """
        xmin,xmax = self.ax.get_xlim()
        labels = [ratingsScale.loc[score,'BB_COMPOSITE'] for score in range(int(xmin),int(xmax+1))]
        self.ax.set_xticks(range(int(xmin),int(xmax+1)))
        self.ax.set_xticklabels(labels)
        z=pandas.np.polyfit(self.xdata,self.ydata,2)
        f=pandas.np.poly1d(z)
        xnew=pandas.np.linspace(xmin,xmax,50)
        self.ax.plot(xnew,f(xnew), linestyle='--')


class TwoPlotChart():
    def __init__(self,title1,data1,title2,data2,labeltextsize,PDF):
        self.title1 = title1
        self.data1 = data1
        self.title2 = title2
        self.data2 = data2
        self.labeltextsize = labeltextsize
        self.PDF = PDF
        self.fig = plt.figure() if PDF == True else Figure()
        self.ax = self.fig.add_axes((0.1,.15,0.8,.7))
        self.ax.set_title(titlelabel)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.fig.subplots_adjust(bottom = 0.1)
        self.ax.scatter(xdata, ydata, marker = '.', c = colors, s = 100)
        for label, x, y in zip(labels, xdata, ydata):
            self.ax.annotate(label,xy = (x, y), xytext = (0, -10),textcoords = 'offset points', ha = 'center', va = 'center', size=labeltextsize)
        self.ax.grid(b=True,which='major',axis='y',linestyle='--')
        self.fig.text(.4,.05, datetime.datetime.today().strftime('%d%b%Y') + ' Credit Trading desk - all data is indicative.',size=labeltextsize)
        self.fig.figimage(logo,10,0)
        gs = gridspec.GridSpec(2, 1,height_ratios=[2,1])
        ax1 = plt.subplot(gs[0])
        ax2 = plt.subplot(gs[1])
        fig.subplots_adjust(hspace=.25)

        pass

class BarChart():
    """BarChart class: Class to define bar charts 

    Attributes:
    self.xlabel : label for x axis 
    self.ylabel : label for y axis 
    self.data : data for bar chart 
    self.labeltextsize : label size 
    self.fig : plt.figure()
    self.ax : Adds axes at positions (left, bottom, width, height). See matplotlib's documentation.

    Methods:
    __init__()
    ytd_performance_template()
    """
    def __init__(self,titlelabel,xlabel,ylabel,data,colors,labeltextsize, PDF):
        """
        Keyword arguments:
        titlelabel : plot title 
        xlabel : x label 
        ylabel : y label 
        data : Bar chart data 
        colors : plot colours 
        labeltextsize : label size 
        """
        self.titlelabel = titlelabel
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.data = data
        self.colors = colors
        self.labeltextsize = labeltextsize
        self.fig = plt.figure() if PDF == True else Figure()
        self.ax = self.fig.add_axes((0.1,.15,0.8,.7))
        self.ax.set_title(titlelabel)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.fig.subplots_adjust(bottom = 0.1)
        self.fig.text(.4,.05, datetime.datetime.today().strftime('%d%b%Y') + ' Credit Trading desk - all data is indicative.',size=self.labeltextsize)
        self.fig.figimage(logo,10,0)

    def ytd_performance_template(self):
        """Function to define template for year-to-date performance charts. Function is called by:
        ChartEngine.ytd_performance()
        """
        #data is a series
        self.data.plot(kind='barh',ax=self.ax, title=self.titlelabel, fontsize=self.labeltextsize, color=self.colors)

    def ytd_range_template(self):
        """Function to define template for year-to-date range. Function is called by:
        ChartEngine.ytd_range()
        """
        #data is a dataframe)
        self.data.plot(kind='bar', stacked=True, ax=self.ax, title=self.titlelabel, fontsize=self.labeltextsize, color=self.colors, legend=False)
        self.ax.set_xticklabels(self.data.index,rotation=45)

    def marketaxess_volume_template(self):
        ewma10d = pandas.ewma(self.data,10)
        ewma10d.plot(ax=self.ax,color='red',lw=3)#,title='Net enquiries and 10 day EWMA')
        self.ax.bar(self.data.index,self.data,align='center')
        xmin,xmax = self.ax.get_xlim()
        newlim = (xmin, matplotlib.dates.date2num(matplotlib.dates.num2date(xmax) + datetime.timedelta(3)))
        self.ax.set_xlim(newlim)


def refresh_bond_universe_very_old():
    """Function to refresh bond universe. Function is called by:
    FlowTradingGUI > MainForm.onUpdateBondUniverse()
    """
    bbgapi=blpapiwrapper.BLP()
    bonds = pandas.ExcelFile(DEFPATH+'bonduniverse.xls').parse('list',index_col=0,has_index_names=True)
    for bond in bonds.index:
        if pandas.isnull(bonds.loc[bond,'COUPON']):
            print 'Updating ' + bond
            for field in bonds.columns:
                if field in ['REGS','144A','TRADITION','BGC','GARBAN','TULLETT','GFI']:
                    continue
                x = bbgapi.bdp(bonds.loc[bond,'REGS']+' Corp',str(field))#otherwise field is u'string'
                if field == 'COUPON' or field == 'AMT_OUTSTANDING':
                    x = float(x)
                if field == 'MATURITY':
                    x = x[5:7]+'/'+x[:2]+'/'+x[:4]
                bonds.loc[bond,field] = x
            print bonds.loc[bond]
    bonds.to_excel(DEFPATH+'bonduniverse.xls','list')
    print 'The file bonduniverse.xls has been updated.'

def refresh_bond_universe():
    """Function to refresh bond universe. Function is called by:
    FlowTradingGUI > MainForm.onUpdateBondUniverse()
    """
    bonds = pandas.ExcelFile(DEFPATH+'bonduniverse.xls').parse('list',index_col=0,has_index_names=True)
    targetBonds = (bonds.loc[pandas.isnull(bonds['SECURITY_NAME']),'REGS']+ ' Corp').to_dict()#this works better than coupon
    targetFields = list(set(bonds.columns)-set(['REGS','144A','TRADITION','BGC','GARBAN','TULLETT','GFI']))
    bonds.loc[targetBonds.keys(),targetFields] = blpapiwrapper.simpleReferenceDataRequest(targetBonds,targetFields)
    print bonds.loc[targetBonds.keys(),targetFields]
    bonds.to_excel(DEFPATH+'bonduniverse.xls','list')
    print 'The file bonduniverse.xls has been updated.'

def refresh_bond_universe_old():
    """Function to refresh bond universe. Function is called by:
    FlowTradingGUI > MainForm.onUpdateBondUniverse()
    """
    bonds = pandas.ExcelFile(DEFPATH+'bonduniverse.xls').parse('list',index_col=0,has_index_names=True)
    targetBonds = bonds[pandas.isnull(bonds['SECURITY_NAME'])]#this works better than coupon
    targetFields = list(set(bonds.columns)-set(['REGS','144A','TRADITION','BGC','GARBAN','TULLETT','GFI']))
    blpts = blpapiwrapper.BLPTS(list(targetBonds['REGS'] + ' Corp'), targetFields)
    blpts.get()
    blpts.closeSession()
    blpts.output['REGS'] = blpts.output.index.str[:-5]
    blpts.output['Bond'] = blpts.output['REGS'].replace(isinsregs)
    blpts.output.set_index('Bond', inplace=True)
    bonds.loc[blpts.output.index,targetFields]=blpts.output
    print blpts.output
    bonds.to_excel(DEFPATH+'bonduniverse.xls','list')
    print 'The file bonduniverse.xls has been updated.'

def create_chart_file(grouplist=['Sub Saharan sovereigns','South Africa','Nigeria','Ukraine sovereign','Russia benchmarks','Russia benchmarks zoom','Central Europe']):
    """Function to create chart file. Function is called by FlowTradingGUI > MainForm.onCreateBondSpreadPDFItem()

    Keyword arguments:
    grouplist : groups of bonds of which plots are to be created. Defaults to the following list if not specified:
                    ['Sub Saharan sovereigns','South Africa','Nigeria','Ukraine sovereign',
                    'Russia benchmarks','Russia benchmarks zoom','Central Europe']
    """
    pp = PdfPages(TEMPPATH+'bondcharts'+datetime.datetime.today().strftime('%d%b%Y')+'.pdf')
    for group in grouplist:#self.bondcharts.columns:
        print ''
        print 'Creating '+group+'...'
        ChartEngine(BONDCHARTS[group].dropna().astype(str),ChartTypes.SpreadDurationPDF,group,False,6,colors=BONDCHARTCOLORS[group].dropna().astype(str),PDF=True)
        pp.savefig()
        plt.close()
    pp.close()
    print ''
    print 'File saved in '+TEMPPATH
    Popen(TEMPPATH+'bondcharts'+datetime.datetime.today().strftime('%d%b%Y')+'.pdf',shell=True)
    pass


class ChartEngine():
    """ChartEngine class : class to define the chart engine.

    Attributes:
    self.bondlist : list of bonds 
    self.bondisins : isins of bonds 
    self.chart_type : Type of chart (SpreadVsDuration, SpreadVsRating, ZScoreVsIndex, YTDRange, YTDPerformance)
    self.title : title of chart 
    self.labeltextsize : size of labels 
    self.df : pandas.DataFrame of bonds 

    Methods:
    __init__()
    plot_group() 
    scatter_plot_zscores()
    ytd_performance()
    ytd_range()
    scatter_plot_rating()
    """

    def __init__(self, bondlist, chart_type, title, show=True, labeltextsize=10, PDF=False, **kwargs):
        """
        Keyword arguments:
        bondlist : list of bonds 
        chart_type : type of chart (SpreadVsDuration, SpreadVsRating, ZScoreVsIndex, YTDRange, YTDPerformance)
        title : title of cahrt 
        show : Defaults to True. False if chart is not to be shown 
        labeltextsize : Size of labels. Defaults to 10.
        """
        self.bondlist = list(bondlist)
        self.bondisins = map(lambda x:bonds.loc[x,'REGS']+ ' Corp',self.bondlist)
        self.chart_type = chart_type
        self.title = title
        self.show = show
        self.labeltextsize = labeltextsize
        self.kwargs = kwargs
        self.df = bonds.loc[bondlist]
        self.output = None
        self.PDF = PDF
        if chart_type == ChartTypes.SpreadVsDuration:
            f = self.plot_group
        if chart_type == ChartTypes.ZScoreVsIndex:
            f = self.scatter_plot_zscores
        if chart_type == ChartTypes.YTDPerformance:
            f = self.ytd_performance
        if chart_type == ChartTypes.YTDRange:
            f = self.ytd_range
        if chart_type == ChartTypes.SpreadVsRating:
            f = self.scatter_plot_rating
        if chart_type == ChartTypes.MAVolume:
            f = self.ma_volume
        if self.PDF == False:
            t = threading.Thread(target=f)
            t.start()
        else:
            f()

    def send_chart(self, chart):
        pub.sendMessage('CHART_READY', message=MessageContainer(chart))

    def plot_group(self):
        """Function to plot spread vs duration for specified group. 
        Function is called by self.__init__ if self.chart_type = ChartTypes.SpreadVsDuration 
        """
        #colors defaults to blue unless specified.
        if 'colors' in self.kwargs:
            colors = self.kwargs['colors']
        else:
            colors = 'blue'
        duration = []
        zspread = []
        blpts = blpapiwrapper.BLPTS(self.bondisins, ['RISK_MID','YAS_ZSPREAD','WORKOUT_OAS_MID_MOD_DUR','OAS_SPREAD_MID'])
        blpts.get()
        for bond in self.bondlist:
            #print bond
            if bond in SPECIALBONDS:
                duration.append(float(blpts.output.loc[bonds.loc[bond,'REGS'] + ' Corp','WORKOUT_OAS_MID_MOD_DUR']))
                zspread.append(float(blpts.output.loc[bonds.loc[bond,'REGS'] + ' Corp','OAS_SPREAD_MID']))
            else:
                duration.append(float(blpts.output.loc[bonds.loc[bond,'REGS'] + ' Corp','RISK_MID']))
                zspread.append(float(blpts.output.loc[bonds.loc[bond,'REGS'] + ' Corp','YAS_ZSPREAD']))
        blpts.closeSession()
        blpts = None
        chart = ScatterChart(self.title,'Risky duration','Z-spread',duration,zspread,self.bondlist,colors,self.labeltextsize, self.PDF)
        chart.ZSpreadTemplate()
        self.send_chart(chart)

    def scatter_plot_zscores(self):
        """Function to plot ZScore versus Index scatter plot. 
        Function is called by self.__init__ if self.chart_type == ChartTypes.ZScoreVsIndex
        """
        if 'source_data' in self.kwargs:
            self.output=self.kwargs['source_data']
        else:
            blpts = blpapiwrapper.BLPTS(self.kwargs['index'] + ' Index','PX_LAST',startDate=datetime.datetime(2013,12,31),endDate=datetime.datetime.today(),periodicity='DAILY')
            hr = HistoryRequest(self.bondisins)
            blpts.register(hr)
            blpts.get()
            blpts.closeSession()
            indexdata=hr.bondisinsDC[self.kwargs['index'] + ' Index'].copy()
            timeframes = [25,75,250]
            self.output = pandas.DataFrame(index=self.bondlist,columns=timeframes)
            blpts = blpapiwrapper.BLPTS(self.bondisins,'BLOOMBERG_MID_G_SPREAD',startDate=datetime.datetime(2013,12,31),endDate=datetime.datetime.today(),periodicity='DAILY')
            hr = HistoryRequest(self.bondisins)
            blpts.register(hr)
            blpts.get()
            blpts.closeSession()
            for bond in self.bondlist:# this is needed as not all time series end at the same point.
                df = hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp']
                df['index'] = indexdata['PX_LAST']
                df.fillna(method='pad',inplace=True)
                df['diff'] = df['BLOOMBERG_MID_G_SPREAD']-df['index']
                lastdiff = df['diff'].iloc[-1]
                self.output.loc[bond] = [(lastdiff-df['diff'].tail(d).mean())/df['diff'].tail(d).std() for d in timeframes]
            # print self.output
            self.output['Sum'] = self.output.sum(axis=1)
            self.output = self.output.applymap(lambda x:int(x*10)/10.)
            #self.output = self.output.sort('Sum',ascending=False)
            self.output.sort_values(by='Sum',ascending=False,inplace=True)
        chart = ScatterChart(self.title,'75 days','250 days',self.output[75],self.output[250],self.output.index,'blue',self.labeltextsize, self.PDF)
        chart.ZScoreTemplate()
        self.send_chart(chart)      
         
    def ytd_performance(self):
        """Function to plot year-to-date performance.
        Function is called by self.__init__ if self.chart_type == ChartTypes.YTDPerformance
        """
        #['ANGOL','ESKOM23','GABON24','GHANA23','IVYCST24','KENINT24','MEMATU','NGERIA23','REPNAM','SENEGL24','SOAF24','ZAMBIN24']
        if 'lastyear' in self.kwargs:
            lastyear = self.kwargs['lastyear']
        else:
            lastyear = 2016
        if 'startdate' in self.kwargs:
            startdate = self.kwargs['startdate']
        else:
            startdate = datetime.datetime(lastyear,12,31)
        startdatedata = startdate - datetime.timedelta(days=7)
        if 'indexlist' in self.kwargs:
            indexlist = self.kwargs['indexlist']
        else:
            indexlist = []
        rows=self.bondlist+indexlist
        indexisins=map(lambda x: x+' Index',indexlist)
        df=pandas.DataFrame(index=rows, columns=['31Dec','today','dP','carry','return','color'])

        blpts = blpapiwrapper.BLPTS(self.bondisins+indexisins,'PX_LAST',startDate=startdatedata,endDate=datetime.datetime.today(),periodicity='DAILY')
        hr = HistoryRequest(self.bondisins)
        blpts.register(hr)
        blpts.get()
        blpts.closeSession()
        blpts=None
        for bond in self.bondlist:
            #print bond
            try:
                idx=hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp'].index.get_loc(startdate, method='pad')
                bondstartdate = startdate
            except:
                #bond only issued this year - will take close of first trading session, not issue price!
                idx=hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp'].index.get_loc(startdate, method='backfill')
                bondstartdate=hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp'].index[0]
                #print bond, bondstartdate
            df.loc[bond,'31Dec']=hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp']['PX_LAST'].iloc[idx]
            df.loc[bond,'today']=hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp']['PX_LAST'].iloc[-1]
            df.loc[bond,'carry']=bonds.loc[bond,'COUPON']*(datetime.datetime.now()-bondstartdate).days*1.0/365
        for index in indexlist:
            idx=hr.bondisinsDC[index+ ' Index'].index.asof(startdate)
            df.loc[index,'31Dec']=hr.bondisinsDC[index+ ' Index']['PX_LAST'].loc[idx]
            df.loc[index,'today']=hr.bondisinsDC[index+ ' Index']['PX_LAST'].iloc[-1]
            df.loc[index,'carry']=0
        df['dP']=df['today']-df['31Dec']
        df['return']=((df['dP']+df['carry'])/df['31Dec'])*100
        #df.sort('return',ascending=True,inplace=True)
        df.sort_values(by='return',ascending=True,inplace=True)
        df.loc[df['return']>=0,'color']='blue'
        df.loc[df['return']<0,'color']='red'
        df.loc[df.index.isin(indexlist),'color']='green'
        self.output=df
        #print df
        chart = BarChart(self.title,'','',df['return'],df['color'],self.labeltextsize, self.PDF)
        chart.ytd_performance_template()
        self.send_chart(chart)                   

    def ytd_range(self):
        """Function to plot year-to-date range.
        Function is called by self.__init__ if self.chart_type == ChartTypes.YTDRange
        """
        if 'lastyear' in self.kwargs:
            lastyear = self.kwargs['lastyear']
        else:
            lastyear = 2016
        if 'startdate' in self.kwargs:
            startdate = self.kwargs['startdate']
        else:
            startdate = datetime.datetime(lastyear,12,31)

        blpts = blpapiwrapper.BLPTS(self.bondisins,'PX_LAST',startDate=startdate,endDate=datetime.datetime.today(),periodicity='DAILY')
        hr = HistoryRequest(self.bondisins)
        blpts.register(hr)
        blpts.get()
        blpts.closeSession()
        blpts=None
        df=pandas.DataFrame(index=self.bondlist,columns=['Price','YTD_low','YTD_high','RangeUp','RangeDown'])
        for bond in self.bondlist:
            #print bond
            df.loc[bond,'YTD_low'] = hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp']['PX_LAST'].min()
            df.loc[bond,'YTD_high'] = hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp']['PX_LAST'].max()
            df.loc[bond,'Price'] = hr.bondisinsDC[bonds.loc[bond,'REGS']+ ' Corp']['PX_LAST'].iloc[-1]
        df['RangeUp'] = df['YTD_high']-df['Price']
        df['RangeDown'] = df['YTD_low']-df['Price']
        self.output = df
        chart = BarChart(self.title,'','Points (0 = current level)',df[['RangeDown','RangeUp']],['r','b'],self.labeltextsize,self.PDF)
        chart.ytd_range_template()
        self.send_chart(chart)              

    def scatter_plot_rating(self):
        """Function to plot Z-spread vs. rating scatter plot.
        Function is called by self.__init__ if self.chart_type == ChartTypes.SpreadVsRating
        """
        df=pandas.DataFrame(index=self.bondlist, columns=['Rating','Z-spread'])
        blpts = blpapiwrapper.BLPTS(self.bondisins,['BB_COMPOSITE','YAS_ZSPREAD'])#,'OAS_SPREAD_MID'])
        blpts.get()
        df=blpts.output.copy()
        blpts.closeSession()
        blpts=None
        rtg=ratingsScale.copy()
        rtg['Score']=rtg.index
        rtg.set_index('BB_COMPOSITE',inplace=True)
        df=df.join(rtg['Score'],on='BB_COMPOSITE')
        df=df[df['Score'].notnull()].copy()
        df['Bond']=df.index.str[:-5]
        df['Bond'] = df['Bond'].replace(isinsregs)        
        df.set_index('Bond',inplace=True)
        df['YAS_ZSPREAD']=df['YAS_ZSPREAD'].astype(float)
        chart = ScatterChart(self.title,'Bloomberg composite rating','Z-spread',df['Score'],df['YAS_ZSPREAD'],df.index,'blue',self.labeltextsize, self.PDF)
        chart.RatingTemplate()
        self.send_chart(chart)

    def ma_volume(self):
        ma_data = ma_analysis.FullMarketAxessData()
        if 'ma_style' in self.kwargs:
            ma_style = self.kwargs['ma_style']
        else:
            ma_style = 'net'
        if 'region' in self.kwargs:
            region = self.kwargs['region']
        else:
            region = 'all'

        if ma_style == 'net':
            if region == 'all':
                subdf = pandas.DataFrame((-ma_data.df['USDQty'].groupby(ma_data.df['Date']).sum()/1000.))
            else:
                grp = ma_data.df.groupby(['Date','Region'])
                data = -grp['USDQty'].sum()/1000.
                data = data.unstack()
                subdf = pandas.DataFrame(data[region])
                subdf.rename(columns={region:'USDQty'},inplace = True)
            chart = BarChart(self.title, 'Date','USD volume (MM)',subdf['USDQty'],'blue',self.labeltextsize,self.PDF)
            chart.marketaxess_volume_template()
            self.send_chart(chart)
        elif ma_style =='full':
            grp = ma_data.df[['AbsUSDQty','USDQty']].groupby(self.df['Date']).sum()/1000.
            grp['USDQty'] = -1.*grp['USDQty']
            grp.rename(columns={'USDQty':'Net','AbsUSDQty':'Gross'},inplace=True)
            grp.tail(30).plot(kind='bar', title='USD enquiry volume (MM)', grid=True)
        elif ma_style =='region':
            grp = ma_data.df.groupby(['Date','Region'])
            data = -grp['USDQty'].sum()
            data = data.unstack()
            data[['Africa','CEE','CIS']].tail(30).plot(kind = 'bar', title='Net enquiries', grid=True)
        else:
            pass



class HistoryRequest(blpapiwrapper.Observer):
    """HistoryRequest Object (Inherits from blpapiwrapper.Observer). Object to stream and record history data from Bloomberg.
    """
    def __init__(self,bondisins):
        self.bondisinsDC={}
    def update(self, *args, **kwargs):
        if kwargs['field']!='ALL':
            self.bondisinsDC[kwargs['security']]=kwargs['data']


def africa_weekly():
    """Function to plot weekly african charts.
    """
    filename='AfricaCreditCharts-'+datetime.datetime.today().strftime('%d%b%Y')+'.pdf'
    pp = PdfPages(TEMPPATH+filename)

    for group in ['Sub Saharan sovereigns', 'South Africa', 'Nigeria', 'African banks']:
        print 'Creating z-spread vs. duration for '+group+'...'
        ChartEngine(BONDCHARTS[group].dropna().astype(str),ChartTypes.SpreadVsDuration,group, False,6,colors=BONDCHARTCOLORS[group].dropna().astype(str), PDF=True)
        pp.savefig()
        plt.close()

    print 'Creating YTD total return...'
    bondlist=BONDCHARTS['Sub Saharan sovereigns'].dropna().astype(str)
    ChartEngine(bondlist,ChartTypes.YTDPerformance,'Year to date total return',False,6,indexlist=['SBAFSOZ','JPEIGLBL'], PDF=True)
    pp.savefig()
    plt.close()

    print 'Creating YTD range...'
    ChartEngine(bondlist,ChartTypes.YTDRange,'Year to date range',False,6, PDF=True)
    pp.savefig()
    plt.close()

    print 'Creating Rating chart...'
    #bondlist=['ANGOL','ESKOM23','ETHOPI','GABON24','GHANA23','IVYCST24','KENINT24','MEMATU','NGERIA23','REPCON','REPNAM25','RWANDA','SENEGL24','SOAF24','ZAMBIN24']#one bond per credit
    ChartEngine(BONDCHARTS['AfricaRating'].dropna().astype(str),ChartTypes.SpreadVsRating,'Spread vs. rating',False,6, PDF=True)
    pp.savefig()
    plt.close()

    print 'Creating Z-score vs. Africa...'
    #bondlist=['ANGOL','ESKOM23','ETHOPI','GABON24','GHANA23','IVYCST24','KENINT24','MEMATU','NGERIA23','REPCON','REPNAM21','RWANDA','SENEGL24','SOAF24','ZAMBIN24']#one bond per credit
    ChartEngine(BONDCHARTS['AfricaZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. Africa index',False,6,index='SBAFSOZS', PDF=True)
    pp.savefig()
    plt.close()

    print 'Creating Z-score vs. EMBI...'
    #bondlist=['ANGOL','ESKOM23','ETHOPI','GABON24','GHANA23','IVYCST24','KENINT24','MEMATU','NGERIA23','REPCON','REPNAM21','RWANDA','SENEGL24','SOAF24','ZAMBIN24']#one bond per credit
    ChartEngine(BONDCHARTS['AfricaZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',False,6,index='JPEIGLBL', PDF=True)
    pp.savefig()
    plt.close()
    pp.close()

    print ''
    print 'File saved in '+TEMPPATH
    Popen(TEMPPATH+filename,shell=True)
    pass

def cee_weekly():
    """Function to plot weekly cee charts.
    """
    filename='CEECreditCharts-'+datetime.datetime.today().strftime('%d%b%Y')+'.pdf'
    pp = PdfPages(TEMPPATH+filename)

    for group in ['CEE USD Benchmarks','CEE EUR Benchmarks']:
        print 'Creating ' + group + ' charts'
        bondlist=BONDCHARTS[group].dropna().astype(str)
        ChartEngine(bondlist,ChartTypes.SpreadVsDuration,group, False,6,colors=BONDCHARTCOLORS[group].dropna().astype(str), PDF=True)
        pp.savefig()
        plt.close()
        ChartEngine(bondlist,ChartTypes.YTDPerformance,'Year to date total return',False,6,indexlist=['JPEIGLBL'], PDF=True)
        pp.savefig()
        plt.close()
        ChartEngine(bondlist,ChartTypes.YTDRange,'Year to date range',False,6, PDF=True)
        pp.savefig()
        plt.close()

    print 'Creating Rating chart...'
    ChartEngine(BONDCHARTS['CEERating'].dropna().astype(str),ChartTypes.SpreadVsRating,'Spread vs. rating',False,6, PDF=True)
    pp.savefig()
    plt.close()

    print 'Creating Z-score vs. EMBI...'
    ChartEngine(BONDCHARTS['CEEZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',False,6,index='JPEIGLBL', PDF=True)
    pp.savefig()
    plt.close()
    pp.close()

    print ''
    print 'File saved in '+TEMPPATH
    Popen(TEMPPATH+filename,shell=True)
    pass

def cis_weekly():
    """Function to plot weekly cee charts.
    """
    filename='CISCreditCharts-'+datetime.datetime.today().strftime('%d%b%Y')+'.pdf'
    pp = PdfPages(TEMPPATH+filename)

    for group in ['CIS Benchmarks']:
        print 'Creating ' + group + ' charts'
        bondlist=BONDCHARTS[group].dropna().astype(str)
        ChartEngine(bondlist,ChartTypes.SpreadVsDuration,group, False,6,colors=BONDCHARTCOLORS[group].dropna().astype(str), PDF=True)
        pp.savefig()
        plt.close()
        ChartEngine(bondlist,ChartTypes.YTDPerformance,'Year to date total return',False,6,indexlist=['JPEIGLBL'], PDF=True)
        pp.savefig()
        plt.close()
        ChartEngine(bondlist,ChartTypes.YTDRange,'Year to date range',False,6, PDF=True)
        pp.savefig()
        plt.close()

    print 'Creating Rating chart...'
    ChartEngine(BONDCHARTS['CISRating'].dropna().astype(str),ChartTypes.SpreadVsRating,'Spread vs. rating',False,6, PDF=True)
    pp.savefig()
    plt.close()

    print 'Creating Z-score vs. EMBI...'
    ChartEngine(BONDCHARTS['CISZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',False,6,index='JPEIGLBL', PDF=True)
    pp.savefig()
    plt.close()

    pp.close()
    print ''
    print 'File saved in '+TEMPPATH
    Popen(TEMPPATH+filename,shell=True)
    pass

def eurozone_weekly():
    """Function to plot weekly Eurozone charts.
    """
    filename='EurozoneCreditCharts-'+datetime.datetime.today().strftime('%d%b%Y')+'.pdf'
    pp = PdfPages(TEMPPATH+filename)

    for group in ['Eurozone']:
        print 'Creating ' + group + ' charts'
        bondlist=BONDCHARTS[group].dropna().astype(str)
        ChartEngine(bondlist,ChartTypes.SpreadVsDuration,group, False,6,colors=BONDCHARTCOLORS[group].dropna().astype(str), PDF=True)
        pp.savefig()
        plt.close()
        ChartEngine(bondlist,ChartTypes.YTDPerformance,'Year to date total return',False,6,indexlist=['JPEIGLBL'], PDF=True)
        pp.savefig()
        plt.close()
        ChartEngine(bondlist,ChartTypes.YTDRange,'Year to date range',False,6, PDF=True)
        pp.savefig()
        plt.close()

    print 'Creating Rating chart...'
    ChartEngine(BONDCHARTS['EurozoneRating'].dropna().astype(str),ChartTypes.SpreadVsRating,'Spread vs. rating',False,6, PDF=True)
    pp.savefig()
    plt.close()

    pp.close()
    print ''
    print 'File saved in '+TEMPPATH
    Popen(TEMPPATH+filename,shell=True)
    pass




def main():
    pass

if __name__ == '__main__':
    main()



