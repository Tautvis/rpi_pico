"""Display to show data."""
import epaper
import time
import utils
import math
from micropython import const

# Colors.
_WHITE = const(0xff)
_BLACK = const(0x00)

_SCALE = {
    'd': 24 * 60 * 60,
    'h': 60 * 60,
    'm': 60,
}


class Display:

    def __init__(self):
        self.epd = epaper.EPD_2in9_Landscape()
        self.full_h = 128
        self.full_w = 296
        self.graph_h = int(128*5/6)
        self.graph_w = 296
        print(f'Display: display size: {self.full_w}x{self.full_h}.')
        print(f'Display: graph size: {self.graph_w}x{self.graph_h}.')

        self.mode = 'candle'
        self.y_axis_scale_step = 200
        self.y_axis_n_ticks = 5

        self.x_axis_n_labels = 7
        self.x_axis_n_ticks = 14
        self.x_axis_step = 30  # 24
        self.x_axis_unit = 'm'  # 'h'
        self.total_x_range = self.x_axis_n_labels * self.x_axis_step * _SCALE[self.x_axis_unit]

        self.plot_extra_v_range = (1, 0)

        # self.time_range = 7 * 24 * 60 * 60  # 7 days.
        self.time_range = self.total_x_range
        # self.time_range = 7 * 60  # 7 minutes for testing.
        # Compute how many seconds in a single pixel.
        self.seconds_per_bin = self.time_range / self.graph_w
        print(f'Display: seconds_per_bin: {self.seconds_per_bin}')

        # Max data size is width of the graph.
        # data[0] is the oldest data point. data[-1] is the newest.
        self.data = []
        self.data_max_size = self.graph_w
        self.last_bin = []
        self.last_ts = 0
        # Two values for printing.
        self.temp = 0.0
        self.last_co2 = 0.0
        self.second_column = ()

        self.init()

    def init(self) -> None:
        """Clear display"""
        self.epd.fill(_WHITE)
        self.epd.display_Base(self.epd.buffer)

    def test_data(self, n: int = 50) -> None:
        """Populate data buffer with random test data."""
        import random
        now = time.time()
        last_mid = random.randint(800, 1200)
        for i in range(n, 0, -1):
            bucket = [utils.clip(last_mid + random.randint(-200, 200),
                                 400, 2000) for _ in range(2)]
            last_mid = (max(bucket) + min(bucket)) // 2
            self.data.append((min(bucket), max(bucket), now-i))

    def set_temp(self, temp: float) -> None:
        """Sets temp to be printed next time."""
        self.temp = temp

    def add(self, value: float, ts: int = None) -> None:
        # ts is in seconds.
        if isinstance(value, (list, tuple, set)):
            for val in value:
                self.add(val, ts=ts)
            return
        if ts is None:
            ts = time.time()
        outdated = self._outdated(ts)
        if outdated:
            self.last_bin.append(value)
            self._process_last_bin(ts)
        self.last_bin.append(value)
        self.last_co2 = value
        if outdated:
            self._update_display()

    def _outdated(self, ts: int) -> bool:
        """Checks if the last bin is outdated."""
        return ts - self.last_ts > self.seconds_per_bin

    def _process_last_bin(self, ts: int) -> None:
        """Process last bin and add to data"""
        # TODO: process multiple skipped buckets.

        time_since_last_bucket = 0
        most_recent_bin = self.data[-1] if self.data else None
        if most_recent_bin:
            pass

        if not self.last_bin:
            self.data.append(None)
        else:
            if self.mode != 'candle':
                raise ValueError(self.mode)
            # For candle mode store: min, max, ts.
            self.data.append((min(self.last_bin), max(self.last_bin), self.last_ts))

        # Reset last bin values.
        self.last_bin = []
        self.last_ts = ts

        # Delete old values, keep the data to max size.
        if len(self.data) > self.data_max_size:
            self.data = self.data[-self.data_max_size:]

    def _calculate_y_axis_limits(self, extra_low: int = 0, extra_high: int = 0) -> tuple[int, int]:
        """Based on data figure min and max y-axis values.
        Compute absolute min/max and then pick the closest round values."""
        if self.mode != 'candle':
            raise ValueError(self.mode)
        # TODO: update to visible range rather than last n samples.
        gmin, gmax = 999999, -999999
        return_defaults = True
        for i in range(min(self.graph_w, len(self.data))):
            if self.data[-i] is None:
                continue
            minv, maxv, _ = self.data[-i]
            gmin = min(gmin, minv)
            gmax = max(gmax, maxv)
            return_defaults = False

        if return_defaults:
            return 400, 1000

        step = self.y_axis_scale_step
        ymin = step * ((gmin//step) - extra_low)
        ymax = step * (math.ceil(gmax/step) + extra_high)
        return int(ymin), int(ymax)

    def set_second_text(self, lines: list[str] = ()) -> None:
        """Sets second column text. Upto three lines."""
        self.second_column = () if not lines else lines[:3]

    def update_text(self, redraw: bool = False) -> None:
        epd = self.epd

        # First column. Max chars: 15 -> 15*8-> 120px
        col1_w = 120
        temp_txt = f'Temp:{self.temp:5.1f} C'
        co2_txt =  f'CO2: {int(self.last_co2):5d} ppm'

        epd.fill_rect(0, 0, col1_w, 10*2, _WHITE)
        epd.text(temp_txt, 0, 0, _BLACK)
        epd.text(co2_txt, 0, 10, _BLACK)

        # Second column.
        col2_w = 120
        col_gap = 6
        col2_h = 3*10
        col2_start = col1_w+col_gap
        epd.fill_rect(col2_start, 0, col2_w, col2_h, _WHITE)
        for i, line in enumerate(self.second_column):
            epd.text(str(line)[:col2_w//8], col2_start, i*10, _BLACK)
        
        if redraw:
            epd.display_Partial(epd.buffer)

    def _update_display(self) -> None:
        # Iterate from the back and draw vertical lines.
        epd = self.epd
        g_left = (self.full_w - self.graph_w)
        g_right = self.full_w

        y_axis_min_val, y_axis_max_val = self._calculate_y_axis_limits(*self.plot_extra_v_range)
        y_axis_range = y_axis_max_val - y_axis_min_val
        assert y_axis_range >= 0
        print(f'Draw: y_axis_range: {y_axis_range}')

        # Read busy
        # TODO

        # Clear
        # epd.Clear(_WHITE)
        epd.fill(_WHITE)

        # Add text
        print('Draw: print text.')
        self.update_text(redraw=False)


        # Plot graph
        print(f'Draw: plot graph from {len(self.data)} points.')
        print(f' - {sum([1 for b in self.data if b is None])} None points.')
        # print(self.data)
        for i in range(len(self.data)):
            if i > self.graph_w:
                # All drawn, this is extra historical range.
                print(' - exceed drawing axis. Stop plotting graph.')
                break
            if self.data[-i] is None:
                continue

            minv, maxv, ts = self.data[-i]

            
            # Draw a single line top to bottom (max val to min val).
            x = g_right - i
            # Relative values are fraction of graph from bottom.
            y_top_rel = (maxv - y_axis_min_val) / y_axis_range
            y_top = int(self.full_h - y_top_rel * self.graph_h)
            y_bot_rel = (minv - y_axis_min_val) / y_axis_range
            y_bot = int(self.full_h - y_bot_rel * self.graph_h)
            h = max(2, y_bot-y_top)
            epd.vline(x, y_top, h, _BLACK)


        ######## Draw axes ########

        # Draw x axis scale.
        x_tick_size_px = 2
        x_axis_label_step_px = self.graph_w // self.x_axis_n_labels
        show_x_label_bg = True
        for i in range(1, self.x_axis_n_labels):
            x = self.full_w - i * x_axis_label_step_px
            y = self.full_h - 8 - x_tick_size_px
            _txt = f'{i*self.x_axis_step}{self.x_axis_unit}'
            x = x - (8//2 * len(_txt))  # Shift text to center over the tick.
            # Char width is 8px.
            if show_x_label_bg:
                epd.rect(x, y, 8*len(_txt), 8, _WHITE, True)
            epd.text(_txt, x, y, _BLACK)
        # Draw x tick marks.
        x_axis_tick_step_px = self.graph_w // self.x_axis_n_ticks
        for i in range(1, self.x_axis_n_ticks):
            x = self.full_w - i * x_axis_tick_step_px
            epd.vline(x, self.full_h-x_tick_size_px, x_tick_size_px, _BLACK)


        # Print y axis scale.
        y_tick_size_px = 2
        # Print y axis labels.
        _single_y_label = True
        if _single_y_label:
            # Single label over two lines.
            # _y_txt = f'{y_axis_min_val}-{y_axis_max_val}'
            # epd.text(_y_txt, self.full_w-(8 * len(_y_txt)), self.full_h-8-self.graph_h, _BLACK)
            _y_txt_1 = f'{y_axis_min_val}-'
            _y_txt_2 = f'{y_axis_max_val}'
            epd.text(_y_txt_1, self.full_w-(8 * len(_y_txt_1)), self.full_h-18-self.graph_h, _BLACK)
            epd.text(_y_txt_2, self.full_w-(8 * len(_y_txt_2)), self.full_h-8-self.graph_h, _BLACK)
        else:
            _min_txt = str(y_axis_min_val)
            epd.text(_min_txt, self.full_w-(8 * len(_min_txt)), self.full_h-8, _BLACK)
            _max_txt = str(y_axis_max_val)
            epd.text(_max_txt, self.full_w-(8 * len(_max_txt)), self.full_h-8-self.graph_h, _BLACK)
        # Draw y tick marks.
        y_axis_tick_step_px = self.graph_h // self.y_axis_n_ticks
        for i in range(self.y_axis_n_ticks):
            y = self.full_h - i * y_axis_tick_step_px
            epd.hline(self.full_w-y_tick_size_px, y, y_tick_size_px, _BLACK)            

        # Draw buffer to screen.
        epd.display_Base(epd.buffer)
