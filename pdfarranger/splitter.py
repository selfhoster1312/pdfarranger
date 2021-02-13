# Copyright (C) 2020 pdfarranger contributors
#
# pdfarranger is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from gi.repository import Gtk
import gettext

_ = gettext.gettext

class Dialog(Gtk.Dialog):
    """ A dialog box to split pages into a grid of pages"""
    def __init__(self, window):
        super().__init__(
            title=_("Split Pages"),
            parent=window,
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK,
                Gtk.ResponseType.OK,
            ),
        )
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_resizable(False)
        self.split_count = {'vertical' : 2, 'horizontal' : 1}
        self.even_splits = {'vertical' : True, 'horizontal' : True}
        self.vmodel = Gtk.ListStore(int, int)
        self.hmodel = Gtk.ListStore(int, int)
        self.model = {'vertical' : self.vmodel, 'horizontal' : self.hmodel}
        self.vspin = Gtk.SpinButton()
        self.hspin = Gtk.SpinButton()
        self.spinbuttons = {'vertical' : self.vspin, 'horizontal' : self.hspin}
        self.vcheck = Gtk.CheckButton()
        self.hcheck = Gtk.CheckButton()
        self.checkbuttons = {'vertical' : self.vcheck, 'horizontal' : self.hcheck}

        hbox = Gtk.HBox()
        self.vbox.pack_start(hbox, True, True, 0)
        for direction in ['vertical', 'horizontal']:
            frame = self._build_frame(direction)
            hbox.pack_start(frame, True, True, 0)
        self.show_all()

    def _build_frame(self, direction):
        frame_txt = {'vertical' : _("Columns"), 'horizontal' : _("Rows")}
        label_txt = {'vertical' : _("Vertical Splits"), 'horizontal' : _("Horizontal Splits")}
        checkbutton_txt = {'vertical' : _("Equal column width"), 'horizontal' : _("Equal row height")}

        frame = Gtk.Frame(label=frame_txt[direction])
        frame.props.margin = 8
        frame.props.margin_bottom = 0
        grid = Gtk.Grid()
        frame.add(grid)
        label = Gtk.Label(label_txt[direction])
        label.set_alignment(0.0, 0.5)
        label.props.margin = 8
        label.props.margin_bottom = 6
        grid.attach(label, 0, 0, width=1, height=1)
        adjustment = Gtk.Adjustment(value=self.split_count[direction], lower=1, upper=20, step_incr=1)
        self.spinbuttons[direction].set_adjustment(adjustment)
        self.spinbuttons[direction].connect("value-changed", self._update_split, direction)
        grid.attach(self.spinbuttons[direction], 1, 0, width=1, height=1)
        self.checkbuttons[direction].set_label(checkbutton_txt[direction])
        self.checkbuttons[direction].set_active(True)
        self.checkbuttons[direction].connect("toggled", self._even_split_toggled, direction)
        grid.attach(self.checkbuttons[direction], 0, 1, width=2, height=1)
        treeview = self._build_model(direction)
        grid.attach(treeview, 0, 2, width=2, height=1)
        return frame

    def _build_model(self, direction):
        label1 = {'vertical' : _("#Col"), 'horizontal' : _("#Row")}
        label2 = {'vertical' : _("Width in %"), 'horizontal' : _("Height in %")}

        split_count = self.split_count[direction]
        for s in range(1, split_count + 1):
            self.model[direction].append([s, 100 // split_count])
        treeview = Gtk.TreeView(model=self.model[direction])
        cr = Gtk.CellRendererText()
        heading = Gtk.TreeViewColumn(label1[direction], cr, text=0)
        treeview.append_column(heading)
        cr = Gtk.CellRendererSpin()
        cr.connect("edited", self._edited, direction)
        cr.set_property("editable", True)
        adjustment = Gtk.Adjustment(value=100, lower=0, upper=100, step_increment=1)
        cr.set_property("adjustment", adjustment)
        heading = Gtk.TreeViewColumn(label2[direction], cr, text=1)
        treeview.append_column(heading)
        return treeview

    def _edited(self, widget, path, value, direction):
        delta = self.model[direction][path][1] - int(value)
        if delta == 0:
            return
        self.model[direction][path][1] = int(value)
        self.checkbuttons[direction].set_active(False)
        for i in reversed(range(len(self.model[direction]))):
            self.model[direction][i][1] = self.model[direction][path][1]

    def _update_split(self, _event, direction):
        self.split_count[direction] = self.spinbuttons[direction].get_value_as_int()
        if self.even_splits[direction]:
            self.model[direction].clear()
            # Partition evenly
            count = self.split_count[direction]
            frac = 100 // count
            partition = [frac] * (count - 1)
            partition.append(100 - (count - 1) * frac)
            for i, frac in enumerate(partition, start = 1):
                self.model[direction].append([i, frac])
        else:
            delta = self.split_count[direction] - len(self.model[direction])
            if delta > 0:
                # Add delta zero rows
                idx = len(self.model[direction]) + 1
                for i in range(delta):
                    self.model[direction].append([idx + i, 0])
            if delta < 0:
                # Delete the last delta entries and ensure that the sum is 100
                s = 0
                for i in range(abs(delta)):
                    s += self.model[direction][-1][1]
                    del self.model[direction][-1]
                self.model[direction][-1][1] += s

    def _even_split_toggled(self, button, direction):
        self.even_splits[direction] = button.get_active()
        self._update_split(None, direction)

    def _crops(self, direction):
        # Pad so that the size calculates crops[i+1] - crops[i].
        crops = [0,0] * (len(self.model[direction]))
        crop_sum = 0
        for i in range(0, len(self.model[direction])):
            crop_sum += self.model[direction][i][1]
        # crop_sum can be > 100 if split with overlap
        # 35,35,35 => [0,35],[32.5,67.5],[65,100]; overlap = 5
        # 60,60 => [0,60],[40,100]; overlap = 20
        # In general:
        #   [start=last-overlap/(pages-1),end=start+width]
        overlap = crop_sum - 100
        pages = len(self.model[direction])
        if pages > 1:
            # There is overlap between pages
            overlap_per_page = overlap/(pages-1)
        else:
            overlap_per_page = 0
        end = overlap_per_page
        for i in range(0, len(self.model[direction])):
            ii = i*2
            value = self.model[direction][i][1]
            start = end - overlap_per_page
            end = start + value
            crops[ii] = start * 0.01
            crops[ii+1] = end * 0.01
        return crops

    def run_get(self):
        result = self.run()
        leftcrops = None
        topcrops = None
        if result == Gtk.ResponseType.OK:
            leftcrops = self._crops('vertical')
            topcrops = self._crops('horizontal')
        self.destroy()
        return leftcrops, topcrops
