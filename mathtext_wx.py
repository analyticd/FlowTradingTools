"""
Container for matplotlib charts. Lightly adapted from http://matplotlib.org/examples/user_interfaces/mathtext_wx.html

"""

import matplotlib
matplotlib.use("WxAgg")
from numpy import arange, sin, pi, cos, log
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure
from guiWidgets import *
import BondTools

import wx

IS_GTK = 'wxGTK' in wx.PlatformInfo
IS_WIN = 'wxMSW' in wx.PlatformInfo
IS_MAC = 'wxMac' in wx.PlatformInfo

############################################################
# This is where the "magic" happens.
from matplotlib.mathtext import MathTextParser
mathtext_parser = MathTextParser("Bitmap")
def mathtext_to_wxbitmap(s):
    ftimage, depth = mathtext_parser.parse(s, 150)
    return wx.BitmapFromBufferRGBA(
        ftimage.get_width(), ftimage.get_height(),
        ftimage.as_rgba_str())
############################################################

functions = [
    (r'$\sin(2 \pi x)$'      , lambda x: sin(2*pi*x)),
    (r'$\frac{4}{3}\pi x^3$' , lambda x: (4.0 / 3.0) * pi * x**3),
    (r'$\cos(2 \pi x)$'      , lambda x: cos(2*pi*x)),
    (r'$\log(x)$'            , lambda x: log(x))
]


class CanvasPanel(wx.Panel):
    def __init__(self,parent, plot_number):
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.NamedColour("WHITE"))

        #self.figure = Figure()
        #self.axes = self.figure.add_subplot(111)
        #self.change_plot(0)

        self.figure,self.axes=return_figure_test(plot_number)

        self.canvas = FigureCanvas(self, -1, self.figure)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        #self.add_buttonbar()
        self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.add_toolbar()  # comment this out for no toolbar


        self.SetSizer(self.sizer)
        self.Fit()

    # def add_buttonbar(self):
    #     self.button_bar = wx.Panel(self)
    #     self.button_bar_sizer = wx.BoxSizer(wx.HORIZONTAL)
    #     self.sizer.Add(self.button_bar, 0, wx.LEFT | wx.TOP | wx.GROW)

    #     for i, (mt, func) in enumerate(functions):
    #         bm = mathtext_to_wxbitmap(mt)
    #         button = wx.BitmapButton(self.button_bar, 1000 + i, bm)
    #         self.button_bar_sizer.Add(button, 1, wx.GROW)
    #         self.Bind(wx.EVT_BUTTON, self.OnChangePlot, button)

    #     self.button_bar.SetSizer(self.button_bar_sizer)

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

    def OnPaint(self, event):
        self.canvas.draw()

    def OnChangePlot(self, event):
        self.change_plot(event.GetId() - 1000)

    def change_plot(self, plot_number):
        t = arange(1.0,3.0,0.01)
        s = functions[plot_number][1](t)
        self.axes.clear()
        self.axes.plot(t, s)
        self.Refresh()

    def change_plot2(self):
        self.axes.clear()
        self.figure,self.axes=return_figure_test(3)
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.Refresh()


class ButtonPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        self.parent=parent
        self.topSizer = wx.BoxSizer(wx.VERTICAL)
        self.buttonSizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        txt1 = wx.StaticText(self, label="Chart type:")
        combo1 = PromptingComboBox(self, 'Spread vs duration', ['Spread vs duration','YTD range'])
        txt2 = wx.StaticText(self, label="Data:")
        combo2 = PromptingComboBox(self, 'Sub Saharan Africa', ['Sub Saharan Africa','Ukraine'])
        btn = wx.Button(self, label = "Draw")
        btn.Bind(wx.EVT_BUTTON, self.onDrawChart) 
        self.sizer1.Add(txt1, 1, wx.ALL, 2)
        self.sizer1.Add(combo1, 1, wx.ALL, 2)
        self.sizer2.Add(txt2, 1, wx.ALL, 2)
        self.sizer2.Add(combo2, 1, wx.ALL, 2)
        self.sizer3.Add(btn, 1, wx.ALL, 2)
        self.buttonSizer.Add(self.sizer1, 0, wx.ALL|wx.EXPAND, 2)
        self.buttonSizer.Add(self.sizer2, 0, wx.ALL|wx.EXPAND, 2)
        self.buttonSizer.Add(self.sizer3, 0, wx.ALL|wx.EXPAND, 2)
        self.topSizer.Add(self.buttonSizer, 0, wx.ALL|wx.EXPAND, 2)
        self.SetSizer(self.topSizer)
        self.Layout()
        pub.subscribe(self.refreshFigure, "CHART_READY")
        pass

    def onDrawChart(self,event):
        #self.chart=BondTools.ChartEngine(['SOAF20','SOAF25'],BondTools.ChartTypes.SpreadVsDuration,'SOAF test',True,10,colors=['blue','blue'])
        self.parent.reDraw2()
        pass

    def refreshFigure(self,message):
        self.parent.reDraw(self.chart.chart.fig)
        pass



class CanvasFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title, size=(550, 850))
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.topPanel=ButtonPanel(self)
        self.bottomPanel=CanvasPanel(self,0)
        self.sizer.Add(self.topPanel,0,wx.ALL|wx.EXPAND)
        self.sizer.Add(self.bottomPanel,0,wx.ALL|wx.EXPAND)
        self.SetSizer(self.sizer)

    def reDraw(self,figure):
        self.bottomPanel.change_plot2(figure)

    def reDraw2(self):
        self.bottomPanel.Destroy()
        self.bottomPanel=CanvasPanel(self,3)
        self.sizer.Add(self.bottomPanel,0,wx.ALL|wx.EXPAND)
        #self.bottomPanel.Layout()
        self.Layout()
        #self.Refresh()



def return_figure_test(plot_number):
    fig=Figure()
    axes=fig.add_subplot(111)
    t = arange(1.0,3.0,0.01)
    s = functions[plot_number][1](t)
    axes.clear()
    axes.plot(t, s)
    return (fig,axes)


class MyApp(wx.App):
    def OnInit(self):
        frame = CanvasFrame(None, "wxPython mathtext demo app")
        self.SetTopWindow(frame)
        frame.Show(True)
        return True

app = MyApp()
app.MainLoop()

