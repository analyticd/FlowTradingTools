"""
Container for matplotlib charts. Lightly based on http://matplotlib.org/examples/user_interfaces/mathtext_wx.html
Written by Alexandre Almosni   alexandre.almosni@gmail.com
(C) 2014-2017 Alexandre Almosni
Released under Apache 2.0 license. More info at http://www.apache.org/licenses/LICENSE-2.0

"""

import wx
import matplotlib
matplotlib.use("WxAgg")
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
import datetime

wxVersion=wx.version()[:3]
if wxVersion=='2.8':
    from wx.lib.pubsub import Publisher as pub
else:
    from wx.lib.pubsub import pub

from BondTools import BONDCHARTS, BONDCHARTCOLORS, ChartEngine, ChartTypes

IS_GTK = 'wxGTK' in wx.PlatformInfo
IS_WIN = 'wxMSW' in wx.PlatformInfo
IS_MAC = 'wxMac' in wx.PlatformInfo

def wxdate2pydate(date):
    """Function to convert wx.datetime to datetime.datetime format
    """
    assert isinstance(date, wx.DateTime)
    if date.IsValid():
        ymd = map(int, date.FormatISODate().split('-'))
        return datetime.datetime(*ymd)
    else:
        return None


class CanvasPanel(wx.Panel):
    """
    This panel holds the actual chart. It is recreated everytime with a new Chart as input.
    """
    def __init__(self, parent, chart):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.NamedColour("WHITE"))
        if chart is not None:
            self.figure,self.axes=chart.fig,chart.ax
        else:
            self.figure=Figure()#WE NEED TO INITIALIZE OTHERWISE IT CAN BREAK
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.add_toolbar()  
        self.SetSizer(self.sizer)
        self.Fit()

    def add_toolbar(self):
        """Copied verbatim from embedding_wx2.py"""
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        if IS_MAC:
            self.SetToolBar(self.toolbar)
        else:
            tw, th = self.toolbar.GetSizeTuple()
            fw, fh = self.canvas.GetSizeTuple()
            self.toolbar.SetSize(wx.Size(fw, th))
            self.sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        self.toolbar.update()


class ButtonPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        self.parent=parent
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.buttonSizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer4 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer5 = wx.BoxSizer(wx.HORIZONTAL)
        txt1 = wx.StaticText(self, label="Chart type:")
        chart_choices=['Spread vs duration','Historical range', 'Historical performance', 'Z-score vs index', 'Spread vs rating', 'MarketAxess volume analysis']
        self.combo1 = wx.ComboBox(self, wx.ID_ANY, 'Spread vs duration', style=wx.CB_DROPDOWN, choices=chart_choices)
        self.Bind(wx.EVT_COMBOBOX, self.onChartTypeSelection,self.combo1)
        txt2 = wx.StaticText(self, label="Data:")
        self.combo2 = wx.ComboBox(self, wx.ID_ANY, list(BONDCHARTS.columns)[0], style=wx.CB_DROPDOWN, choices=list(BONDCHARTS.columns))
        txt3 = wx.StaticText(self, label="Start date for historical charts:")
        self.startcalendar = wx.DatePickerCtrl(self, wx.ID_ANY, wx.DateTimeFromDMY(31,11,datetime.datetime.now().year-1))
        self.btn = wx.Button(self, label = "Draw")
        self.btn.Bind(wx.EVT_BUTTON, self.onDrawChart) 
        self.txt4 = wx.StaticText(self, label="Ready")
        self.sizer1.Add(txt1, 1, wx.ALL, 2)
        self.sizer1.Add(self.combo1, 1, wx.ALL, 2)
        self.sizer2.Add(txt2, 1, wx.ALL, 2)
        self.sizer2.Add(self.combo2, 1, wx.ALL, 2)
        self.sizer3.Add(txt3, 1, wx.ALL, 2)
        self.sizer3.Add(self.startcalendar, 1, wx.ALL, 2)
        self.sizer4.Add(self.btn, 1, wx.ALL, 2)
        self.sizer5.Add(self.txt4,1,wx.ALL,2)
        self.buttonSizer.Add(self.sizer1, 0, wx.ALL|wx.EXPAND, 2)
        self.buttonSizer.Add(self.sizer2, 0, wx.ALL|wx.EXPAND, 2)
        self.buttonSizer.Add(self.sizer3, 0, wx.ALL|wx.EXPAND, 2)
        self.buttonSizer.Add(self.sizer4, 0, wx.ALL|wx.EXPAND, 2)
        self.buttonSizer.Add(self.sizer5, 0, wx.ALL|wx.EXPAND, 2)
        self.topSizer.Add(self.buttonSizer, 0, wx.ALL|wx.EXPAND, 2)
        self.SetSizer(self.topSizer)
        self.Layout()
        self.embiZscores = None
        self.africaZscores = None
        self.africaEMBIZscores = None
        self.ceeZscores = None
        pass

    def onChartTypeSelection(self,event):
        self.chartType = self.combo1.GetValue()
        if self.chartType in ['Spread vs duration', 'Historical range', 'Historical performance']:
            self.combo2.Clear()
            self.combo2.AppendItems(list(BONDCHARTS.columns))
        elif self.chartType == 'Z-score vs index':
            self.combo2.Clear()
            self.combo2.AppendItems(['Benchmark bonds vs. EMBI', 'SSA bonds vs. Africa index', 'SSA bonds vs. EMBI','CEE bonds vs. EMBI','CIS bonds vs. EMBI'])
        elif self.chartType == 'Spread vs rating':
            self.combo2.Clear()
            self.combo2.AppendItems(['EMBI','Africa','CEE','CIS', 'Eurozone'])
        elif self.chartType == 'MarketAxess volume analysis':
            self.combo2.Clear()
            self.combo2.AppendItems(['Net enquiry total','Net enquiry Africa','Net enquiry CIS','Net enquiry CEE','Gross enquiry total'])
        else:
            pass
        self.combo2.SetSelection(0)

    def onDrawChart(self,event):
        self.txt4.SetLabel('Drawing, please wait...')
        self.btn.Disable()
        chartTypeString = self.combo1.GetValue()
        chartSubTypeString = self.combo2.GetValue()
        startdate = wxdate2pydate(self.startcalendar.GetValue())
        if chartTypeString == 'Spread vs duration':
            group = chartSubTypeString
            ChartEngine(BONDCHARTS[group].dropna().astype(str),ChartTypes.SpreadVsDuration,group,True,10,colors=BONDCHARTCOLORS[group].dropna().astype(str))
        elif chartTypeString == 'Historical range':
            group = chartSubTypeString
            ChartEngine(BONDCHARTS[group].dropna().astype(str),ChartTypes.YTDRange,group,True,10,colors=BONDCHARTCOLORS[group].dropna().astype(str), startdate=startdate)
        elif chartTypeString == 'Historical performance':
            group = chartSubTypeString
            ChartEngine(BONDCHARTS[group].dropna().astype(str),ChartTypes.YTDPerformance,group,True,10,indexlist=['JPEIGLBL'], startdate=startdate)
        elif chartTypeString == 'Z-score vs index':
            if chartSubTypeString == 'Benchmark bonds vs. EMBI':
                if self.embiZscores is None:
                    self.txt4.SetLabel('Found existing...')
                    x=ChartEngine(BONDCHARTS['EMBIZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,index='JPEIGLBL')
                    self.embiZscores=x.output
                else:
                    ChartEngine(BONDCHARTS['EMBIZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,source_data=self.embiZscores)
            elif chartSubTypeString == 'SSA bonds vs. Africa index':
                if self.africaZscores is None:
                    x=ChartEngine(BONDCHARTS['AfricaZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. Africa index',True,10,index='SBAFSOZS')
                    self.africaZscores=x.output
                else:
                    ChartEngine(BONDCHARTS['AfricaZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. Africa index',True,10,source_data=self.africaZscores)
            elif chartSubTypeString == 'SSA bonds vs. EMBI':
                if self.africaEMBIZscores is None:
                    x=ChartEngine(BONDCHARTS['AfricaZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,index='JPEIGLBL')
                    self.africaEMBIZscores=x.output
                else:
                    ChartEngine(BONDCHARTS['AfricaZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,source_data=self.africaEMBIZscores)
            elif chartSubTypeString == 'CEE bonds vs. EMBI':
                if self.ceeZscores is None:
                    x=ChartEngine(BONDCHARTS['CEEZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,index='JPEIGLBL')
                    self.ceeZscores=x.output
                else:
                    ChartEngine(BONDCHARTS['CEEZScores'].dropna().astype(str),ChartTypes.ZScoreVsIndex,'Historical Z-score vs. EMBI',True,10,source_data=self.ceeZscores)
            else:
                pass
        elif chartTypeString == 'Spread vs rating':
            if chartSubTypeString == 'EMBI':
                ChartEngine(BONDCHARTS['EMBIRating'].dropna().astype(str),ChartTypes.SpreadVsRating,'EMBI spread vs. rating',True,10)
            elif chartSubTypeString == 'Africa':
                ChartEngine(BONDCHARTS['AfricaRating'].dropna().astype(str),ChartTypes.SpreadVsRating,'Africa spread vs. rating',True,10)
            elif chartSubTypeString == 'CEE':
                ChartEngine(BONDCHARTS['CEERating'].dropna().astype(str),ChartTypes.SpreadVsRating,'CEE spread vs. rating',True,10)
            elif chartSubTypeString == 'Eurozone':
                ChartEngine(BONDCHARTS['EurozoneRating'].dropna().astype(str),ChartTypes.SpreadVsRating,'Eurozone spread vs. rating',True,10)
            else:
                pass
        elif chartTypeString == 'MarketAxess volume analysis':
            if chartSubTypeString == 'Net enquiry total':
                ChartEngine([],ChartTypes.MAVolume,'Net enquiry total',True,10)
            elif chartSubTypeString == 'Net enquiry Africa':
                ChartEngine([],ChartTypes.MAVolume,'Net enquiry Africa',True,10,ma_style='net',region='Africa')
            elif chartSubTypeString == 'Net enquiry CIS':
                ChartEngine([],ChartTypes.MAVolume,'Net enquiry CIS',True,10,ma_style='net',region='CIS')
            elif chartSubTypeString == 'Net enquiry CEE':
                ChartEngine([],ChartTypes.MAVolume,'Net enquiry CEE',True,10,ma_style='net',region='CEE')
            else:
                pass




class ChartingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.topPanel=ButtonPanel(self)
        self.bottomPanel=CanvasPanel(self,None)
        self.sizer.Add(self.topPanel,0,wx.ALL|wx.EXPAND)
        self.sizer.Add(self.bottomPanel,1,wx.ALL|wx.EXPAND)
        self.SetSizer(self.sizer)
        pub.subscribe(self.reDraw, "CHART_READY")

    def reDraw(self,message):
        wx.CallAfter(self.doRedraw, message)

    def doRedraw(self, message):
        self.bottomPanel.Destroy()
        self.bottomPanel=CanvasPanel(self,message.data)
        self.sizer.Add(self.bottomPanel,1,wx.ALL|wx.EXPAND)
        self.Layout()
        self.topPanel.btn.Enable()
        self.topPanel.txt4.SetLabel('Ready')


class ChartFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Charting tool",size=(925,850))
        self.panel=ChartingPanel(self)


if __name__ == "__main__":
    app = wx.App()
    frame = ChartFrame().Show()
    app.MainLoop()

