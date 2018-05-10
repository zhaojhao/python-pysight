import unittest

from pysight.nd_hist_generator.allocation_tools import *


class TestAllocation(unittest.TestCase):

    df_photons = pd.DataFrame(np.arange(10), columns=['abs_time'])
    dict_of_data = dict(Frames=pd.DataFrame(np.arange(0, 100, 10, dtype=np.uint64),
                                            columns=['abs_time']),
                        Lines=pd.DataFrame(np.arange(0, 100, 5, dtype=np.uint64),
                                           columns=['abs_time']))
    # allocat = Allocate(df_photons.copy(), dict_of_data.copy())

    def test_reindex_dict_of_data_standard_frames(self):
        allocat = Allocate(self.df_photons.copy(), self.dict_of_data.copy())
        allocat._Allocate__reindex_dict_of_data()
        true_frames = pd.Series(data=self.dict_of_data['Frames'].abs_time.values,
                                index=self.dict_of_data['Frames'].abs_time.values)
        np.testing.assert_equal(allocat.dict_of_data['Frames'].values,
                                true_frames.values)
        np.testing.assert_equal(allocat.dict_of_data['Frames'].index.values,
                                true_frames.index.values)

    def test_reindex_dict_of_data_standard_lines(self):
        allocat = Allocate(self.df_photons.copy(), self.dict_of_data.copy())
        allocat._Allocate__reindex_dict_of_data()
        lines = self.dict_of_data['Lines'].abs_time.values
        frames = np.repeat(self.dict_of_data['Frames'].abs_time.values.copy(), 2)
        np.testing.assert_equal(allocat.dict_of_data['Lines'].values,
                                lines)
        np.testing.assert_equal(allocat.dict_of_data['Lines'].index.values,
                                frames)

    def test_reindex_dict_of_data_lines_before_start_of_frames(self):
        frames = pd.DataFrame(np.arange(30, 100, 10, dtype=np.uint64),
                              columns=['abs_time'])
        lines = pd.DataFrame(np.arange(0, 100, 5, dtype=np.uint64),
                             columns=['abs_time'])
        dict_of_data = dict(Frames=frames, Lines=lines)
        allocat = Allocate(self.df_photons.copy(), dict_of_data)
        allocat._Allocate__reindex_dict_of_data()
        lines = lines.abs_time.values
        np.testing.assert_equal(allocat.dict_of_data['Lines'].values,
                                lines[6:])
        np.testing.assert_equal(allocat.dict_of_data['Lines'].index.values,
                                np.repeat(frames.abs_time.values.copy(), 2))

    def test_reindex_dict_of_data_lines_much_after_last_frame(self):
        frames = pd.DataFrame(np.arange(30, 100, 10, dtype=np.uint64),
                              columns=['abs_time'])
        lines = pd.DataFrame(np.arange(0, 150, 5, dtype=np.uint64),
                             columns=['abs_time'])
        dict_of_data = dict(Frames=frames, Lines=lines)
        allocat = Allocate(self.df_photons.copy(), dict_of_data)
        allocat._Allocate__reindex_dict_of_data()
        lines = lines.abs_time.values
        np.testing.assert_equal(allocat.dict_of_data['Lines'].values,
                                lines[6:])
        frames = np.repeat(frames.abs_time.values.copy(), 2)
        frames = np.concatenate((frames, np.repeat(np.array([90]), 10)))
        np.testing.assert_equal(allocat.dict_of_data['Lines'].index.values, frames)