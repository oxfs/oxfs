#!/usr/bin/env python

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

class XlxToGraph(object):
    def __init__(self):
        self.oxfs_iozone_xls = './oxfs_iozone.xls'
        self.sshfs_iozone_xls = './sshfs_iozone.xls'
        self.oxfs_xls = pd.read_excel(self.oxfs_iozone_xls)
        self.sshfs_xls = pd.read_excel(self.sshfs_iozone_xls)
        matplotlib.rcParams['font.sans-serif'] = ['monofur']

    def float2(self, x):
        return int(x * 100) / 100

    def draw_one(self, xls, title, color):
        title = '{} ({})'.format(title, xls.columns[0])
        column_a = xls[xls.columns[0]]
        column_c = xls[xls.columns[2]]

        ticks = [column_a[x] for x in range(3, 16)]
        kbps = [self.float2(column_c[x]) for x in range(3, 16)]
        plt.barh(range(16 - 3), kbps, height=0.2, color=color, alpha=0.8)
        plt.yticks(range(16 - 3), ticks)
        plt.xlim(0, max(kbps) * 1.2)
        plt.xlabel("Speed")
        plt.title(title)
        for x, y in enumerate(kbps):
            plt.text(y + 1000, x - 0.1, '%s KB/s' % y)

        plt.show()

    def draw_compare(self):
        xls = self.oxfs_xls
        column_a = xls[xls.columns[0]]
        column_c = xls[xls.columns[2]]

        oxfs_ticks = [column_a[x] + '- oxfs' for x in range(3, 16)]
        oxfs_kbps = [self.float2(column_c[x]) for x in range(3, 16)]

        xls = self.sshfs_xls
        column_a = xls[xls.columns[0]]
        column_c = xls[xls.columns[2]]

        sshfs_ticks = [column_a[x] + '- sshfs' for x in range(3, 16)]
        sshfs_kbps = [self.float2(column_c[x]) for x in range(3, 16)]

        ticks = []
        kbps = []
        for i in range(0, len(oxfs_kbps)):
            ticks.append(oxfs_ticks[i])
            ticks.append(sshfs_ticks[i])
            kbps.append(oxfs_kbps[i])
            kbps.append(sshfs_kbps[i])

        barlist = plt.barh(range(len(kbps)), kbps, height=0.3, color='coral', alpha=0.8)
        for bar in barlist[1::2]:
            bar.set_color('slateblue')
        plt.yticks(range(len(ticks)), ticks)
        plt.xlim(0, max(kbps) * 1.2)
        for x, y in enumerate(kbps):
            plt.text(y + 1000, x - 0.1, '%s KB/s' % y)

        title = 'Oxfs Vs Sshfs ({})'.format(xls.columns[0])
        plt.title(title)
        plt.xlabel("Speed")

        plt.show()

xls2graph = XlxToGraph()
xls2graph.draw_one(xls2graph.oxfs_xls, 'Oxfs', 'coral')

xls2graph = XlxToGraph()
xls2graph.draw_one(xls2graph.sshfs_xls, 'Sshfs', 'slateblue')

xls2graph = XlxToGraph()
xls2graph.draw_compare()
