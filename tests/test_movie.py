from unittest import TestCase
from pysight.nd_hist_generator.movie_tools import *
from pysight.nd_hist_generator.volume_gen import *
import pandas as pd
import numpy as np


def gen_data_df(frame_num=10, line_num=1000, end=100000):
    """
    Mock data for tests.
    Returns:
        df - The full DataFrame
        lines only
        x pixels
        y pixels
    """
    photons = np.arange(0, end, dtype=np.uint64)
    channel = np.ones_like(photons)
    lines = np.linspace(0, end, num=line_num, endpoint=False, dtype=np.uint64)
    x_pix = int(len(photons) / len(lines))
    ones_lines = np.ones((1, int(len(photons) / len(lines))),
                         dtype=np.uint64)
    frames = np.linspace(0, end, num=frame_num, dtype=np.uint64, endpoint=False)
    ones_frames = np.ones((1, int(len(photons) / len(frames))),
                          dtype=np.uint64)
    lines = (np.atleast_2d(lines).T @ ones_lines).ravel()
    frames = (np.atleast_2d(frames).T @ ones_frames).ravel()
    assert len(lines) == len(frames) == len(photons)

    df = pd.DataFrame({'abs_time': photons,
                       'time_rel_line': photons - lines,
                       'Lines': lines, 'Frames': frames,
                       'Channel': channel})
    df.set_index(['Channel', 'Frames', 'Lines'], drop=True, inplace=True)
    y_pix = x_pix
    return df, pd.Series(np.unique(lines)), x_pix, y_pix


class TestMovies(TestCase):
    frame_num = 10
    end = 100000
    data, lines, x_pix, y_pix = gen_data_df(frame_num=frame_num, end=end)
    data_shape = (frame_num, x_pix, y_pix)
    fr = VolumeGenerator(data, data_shape).create_frame_slices()
    movie = Movie(data, lines, data_shape=data_shape,
                  outputs={'memory': True}, line_delta=int(lines.diff().mean()),
                  fill_frac=100., bidir=True, frames=fr)
    movie.run()

    def test_all_pipeline_basic(self):
        self.assertFalse(np.all(self.movie.stack[1].ravel() == np.ones((self.end,), dtype=np.uint8)))
        ### SHOULD NOT FAIL, BUT DOES DUE TO HISTOGRAMDD BUG ###

    def test_baseline_outputs(self):
        during, end = self.movie._Movie__determine_outputs()
        self.assertTrue(len(during) == 1)
        self.assertTrue(len(end) == 1)
        during, end = str(during), str(end)
        self.assertTrue('create_memory_output' in during)
        self.assertTrue('convert_deque_to_arr' in end)

    def test_slice_df(self):
        sl = slice(0, 23000)
        movie = Movie(self.data, self.lines, data_shape=self.data_shape,
                      outputs={'memory': True}, line_delta=int(self.lines.diff().mean()),
                      fill_frac=100., bidir=True,
                      frames=(slice(1) for n in range(2)))
        di = movie._Movie__slice_df(sl)
        self.assertTrue(1 in di[0].keys())
        self.assertSequenceEqual((di[0][1].shape, di[1]), ((30000, 2), 3))

    def test_single_slice_df(self):
        sl = slice(0, 0)
        movie = Movie(self.data, self.lines, data_shape=self.data_shape,
                      outputs={'memory': True}, line_delta=int(self.lines.diff().mean()),
                      fill_frac=100., bidir=True,
                      frames=(slice(1) for n in range(2)))
        di = movie._Movie__slice_df(sl)
        self.assertTrue(1 in di[0].keys())
        self.assertSequenceEqual((di[0][1].shape, di[1]), ((10000, 2), 1))
