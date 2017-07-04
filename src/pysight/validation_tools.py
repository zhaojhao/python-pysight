"""
__author__ = Hagai Hargil
"""
from typing import Dict, List, Union
import pandas as pd
import numpy as np
import warnings


def extrapolate_line_data(last_event: int, line_point: int=0,
                          line_delta: int=0, num_of_lines: int=1,
                          delay_between_frames: float=0.0011355,
                          bidir: bool=False, binwidth: float=800e-12) -> pd.DataFrame:
    """
    From a single line signal extrapolate the presumed line data vector. The line frequency is doubled
    the original frequency. If needed, events will be discarded later.
    :param last_event: The last moment of the experiment
    :param line_delta: Bins between subsequent lines.
    :param line_point: Start interpolation from this point.
    :param num_of_lines: Number of lines in a frame.
    :param delay_between_frames: Time (in sec) between frames.
    :param bidir: Whether the scan was bidirectional.
    :param binwidth: Binwidth of multiscaler in seconds.
    :return: pd.DataFrame of line data
    """
    line_vec = np.arange(start=line_point, stop=last_event, step=line_delta,
                         dtype=np.uint64)

    line_vec = np.r_[np.flip(np.arange(start=line_point, stop=0, step=-line_delta,
                               dtype=np.uint64)[1:], axis=0), line_vec]

    # Check if 0 should be included
    if line_vec[0] - line_delta == 0:
        line_vec = np.r_[0, line_vec]

    # Add frame delay
    step_between_frames = num_of_lines if bidir else num_of_lines * 2
    delay_between_frames_in_bins = int(delay_between_frames / binwidth)
    indices_of_addition = np.arange(step_between_frames, len(line_vec), step=step_between_frames)
    for idx in indices_of_addition:
        line_vec[idx:] = line_vec[idx:] + delay_between_frames_in_bins

    return pd.DataFrame(line_vec, columns=['abs_time'], dtype=np.uint64)

def bins_bet_lines(line_freq: float=0, binwidth: float=0,
                   lines: Union[int, pd.DataFrame]=0, bidir: bool=False) -> int:
    """
    Calculate number of bins between lines, and half it because of possible bidirectional scanning
    :param lines: Raw data of lines, if it exists.
    :return: int
    """
    if type(lines) == int:
        freq_in_bins = 1/(line_freq * binwidth)
        return int(freq_in_bins / 2)
    else:
        line_diff = lines['abs_time'].diff()
        max_change_pct = lines['abs_time'][line_diff.pct_change(periods=10) > 5]  # 5 percent change is allowed
        if len(max_change_pct) / len(lines) < 0.05:
            return int(line_diff.median() if bidir else line_diff.median() / 2)
        else:  # line data is corrupt, build lines from scratch
            freq_in_bins = 1 / (line_freq * binwidth)
            return int(freq_in_bins / 2)


def validate_line_input(dict_of_data: Dict, cols_in_data: List, num_of_lines: int=-1,
                        num_of_frames: int=-1, binwidth: float=800e-12,
                        last_event_time: int=-1, bidir: bool=False):
    """ Verify that the .lst input of lines exists and looks fine. Create one if there's no such input. """
    if num_of_lines == -1:
        raise ValueError('No number of lines input received.')

    if num_of_frames == -1:
        raise ValueError('No number of frames received.')

    if last_event_time == -1:
        raise ValueError('No last event time received.')

    if len(cols_in_data) == 0:
        raise ValueError('No columns in data.')

    if 'Lines' in dict_of_data.keys():
        # Verify that the input is not corrupt
        max_change_pct = dict_of_data['Lines']['abs_time'][dict_of_data['Lines']['abs_time']\
            .diff().pct_change(periods=10) > 15]
        if len(max_change_pct) / dict_of_data['Lines'].shape[0] > 0.1\
            and 'Frames' not in dict_of_data:
            # Data is corrupted, and no frame channel can help us.
            raise ValueError(""" Line data was corrupt.
                             Please rerun PySight without a line channel.""")

        elif len(max_change_pct) / dict_of_data['Lines'].shape[0] > 0.1\
            and 'Frames' in dict_of_data:
            # Data is corrupted, but we can rebuild lines on top of the frame channel
            line_array = create_line_array(last_event_time=last_event_time, num_of_lines=num_of_lines,
                                           num_of_frames=num_of_frames)
            dict_of_data['Lines'] = pd.DataFrame(line_array, columns=['abs_time'], dtype='uint64')
            line_delta = last_event_time / (num_of_lines * int(num_of_frames))
            return dict_of_data, line_delta

        elif len(max_change_pct) / len(dict_of_data['Lines']) < 0.1:
            # Data is valid. Check whether we need a 0-time line event
            line_delta = dict_of_data['Lines'].loc[:, 'abs_time'].diff().mean()
            zeroth_line_delta = np.abs(dict_of_data['Lines'].loc[0, 'abs_time'] - line_delta)/line_delta
            if zeroth_line_delta < 0.05:
                dict_of_data['Lines'] = pd.DataFrame([[0] * len(cols_in_data)],
                                                     columns=cols_in_data,
                                                     dtype='uint64')\
                    .append(dict_of_data['Lines'], ignore_index=True)
            return dict_of_data, line_delta

    else:  # create our own line array
        line_array = create_line_array(last_event_time=last_event_time, num_of_lines=num_of_lines,
                                       num_of_frames=num_of_frames)
        dict_of_data['Lines'] = pd.DataFrame(line_array, columns=['abs_time'], dtype='uint64')
        line_delta = last_event_time / (num_of_lines * int(num_of_frames))
        return dict_of_data, line_delta


def validate_frame_input(dict_of_data: Dict, binwidth, cols_in_data: List, line_delta: int=-1, num_of_lines: int=-1,
                         last_event_time: int=-1, bidir: bool=False):
    if line_delta == -1:
        raise ValueError('No line delta input received.')

    if num_of_lines == -1:
        raise ValueError('No number of lines received.')

    if last_event_time == -1:
        raise ValueError('No last event time input received.')

    if len(cols_in_data) == 0:
        raise ValueError('No columns in data.')

    if 'Frames' in dict_of_data.keys():
        dict_of_data['Frames'] = pd.DataFrame([[0] * len(cols_in_data)],
                                              columns=cols_in_data,
                                              dtype='uint64')\
            .append(dict_of_data['Frames'], ignore_index=True)
    else:
        frame_array = create_frame_array(lines=dict_of_data['Lines'].loc[:, 'abs_time'],
                                         last_event_time=last_event_time,
                                         pixels=num_of_lines, bidir=bidir)
        dict_of_data['Frames'] = pd.DataFrame(frame_array, columns=['abs_time'], dtype='uint64')

    return dict_of_data


def create_frame_array(lines: pd.Series=None, last_event_time: int=None,
                       pixels: int=None, bidir: bool=False) -> np.ndarray:
    """Create a pandas Series of start-of-frame times"""

    if last_event_time is None or pixels is None or lines.empty:
        raise ValueError('Wrong input detected.')

    if last_event_time <= 0:
        raise ValueError('Last event time is zero or negative.')

    lines_for_frame_generation = lines.values if bidir else lines[::2].values
    num_of_recorded_lines = lines_for_frame_generation.shape[0]
    actual_num_of_frames = max(num_of_recorded_lines // pixels, 1)

    if num_of_recorded_lines < pixels:
        array_of_frames = np.linspace(start=0, stop=last_event_time, num=int(actual_num_of_frames),
                                      endpoint=False, dtype=np.uint64)
    else:
        unnecess_lines = num_of_recorded_lines % pixels
        array_of_frames = lines_for_frame_generation[0 : int(num_of_recorded_lines-unnecess_lines) : pixels]

    return array_of_frames


def create_line_array(last_event_time: int=None, num_of_lines=None, num_of_frames=None) -> np.ndarray:
    """Create a pandas Series of start-of-line times"""

    if (last_event_time is None) or (num_of_lines is None) or (num_of_frames is None):
        raise ValueError('Wrong input detected.')

    if (num_of_lines <= 0) or (num_of_frames <= 0):
        raise ValueError('Number of lines and frames has to be positive.')

    if last_event_time <= 0:
        raise ValueError('Last event time is zero or negative.')

    total_lines = num_of_lines * int(num_of_frames)
    line_array = np.arange(start=0, stop=last_event_time, step=last_event_time/total_lines, dtype=np.uint64)
    return line_array


def validate_created_data_channels(dict_of_data: Dict):
    """
    Make sure that the dictionary that contains all data channels makes sense.
    """
    assert {'PMT1', 'Lines', 'Frames'} <= set(dict_of_data.keys())  # A is subset of B

    if dict_of_data['Frames'].shape[0] > dict_of_data['Lines'].shape[0]:  # more frames than lines
        raise UserWarning('More frames than lines, consider replacing the two.')

    try:
        if dict_of_data['TAG Lens'].shape[0] < dict_of_data['Lines'].shape[0]:
            raise UserWarning('More lines than TAG pulses, consider replacing the two.')
    except KeyError:
        pass

    try:
        if dict_of_data['Laser'].shape[0] < dict_of_data['Lines'].shape[0] or \
           dict_of_data['Laser'].shape[0] < dict_of_data['Frames'].shape[0]:
            raise UserWarning('Laser pulses channel contained less ticks than the Lines or Frames channel.')
    except KeyError:
        pass

    try:
        if dict_of_data['Laser'].shape[0] < dict_of_data['TAG Lens'].shape[0]:
            raise UserWarning('Laser pulses channel contained less ticks than the TAG lens channel.')
    except KeyError:
        pass


def validate_laser_input(pulses, laser_freq: float, binwidth: float, offset: int) -> pd.Series:
    """
    Create an orderly laser pulse train.
    :param pulses:
    :param laser_freq:
    :return:
    """
    import warnings

    diffs = pulses.loc[:, 'abs_time'].diff()
    rel_idx = (diffs <= np.ceil((1 / (laser_freq * binwidth)))) & (diffs >= np.floor((1 / (laser_freq * binwidth))))
    pulses_final = pulses[rel_idx]  # REMINDER: Laser offset wasn't added
    if len(pulses_final) < 0.9 * len(pulses):
        warnings.warn("More than 10% of pulses were filtered due to bad timings. Make sure the laser input is fine.")

    pulses_final = pd.concat([pulses.loc[:0, :], pulses_final])  # Add back the first pulse
    pulses_final.reset_index(drop=True, inplace=True)

    return pulses_final


def rectify_photons_in_uneven_lines(df: pd.DataFrame, sorted_indices: np.array, lines: pd.Series, bidir: bool = True,
                                    phase: float = 0, keep_unidir: bool = False):
    """
    "Deal" with photons in uneven lines. Unidir - if keep_unidir is false, will throw them away.
    Bidir = flips them over.
    """
    uneven_lines = np.remainder(sorted_indices, 2)
    if bidir:
        time_rel_line = pd.Series(range(df.shape[0]), dtype='int64', name='time_rel_line')
        time_rel_line.loc[uneven_lines == 0] = df.loc[uneven_lines == 0, 'time_rel_line_pre_drop'].values
        # Reverse the relative time of the photons belonging to the uneven lines,
        # by subtracting their relative time from the start time of the next line
        lines_to_subtract_from = lines.loc[sorted_indices[uneven_lines.astype(bool)] + 1].values
        events_to_subtract = df.loc[np.logical_and(uneven_lines, 1), 'abs_time'].values
        time_rel_line.iloc[uneven_lines.nonzero()[0]] = lines_to_subtract_from - events_to_subtract \
            + (np.sin(phase) * lines[1])  # introduce phase delay between lines
        df.insert(loc=len(df.columns), value=time_rel_line.values, column='time_rel_line')

    if not bidir and not keep_unidir:
        df = df.loc[uneven_lines != 1, :].copy()
        df.rename(columns={'time_rel_line_pre_drop': 'time_rel_line'}, inplace=True)

    if not bidir and keep_unidir:  # Unify the excess rows and photons in them into the previous row
        sorted_indices[np.logical_and(uneven_lines, 1)] -= 1
        df.loc['Lines'] = lines.loc[sorted_indices].values

    try:
        df.drop(['time_rel_line_pre_drop'], axis=1, inplace=True)
    except KeyError:  # column label doesn't exist
        pass
    except ValueError:
        pass
    df = df.loc[df.loc[:, 'time_rel_line'] >= 0]

    return df


def calc_last_event_time(dict_of_data: Dict, lines_per_frame: int=-1):
    """
    Find the last event time for the experiment. Logic as follows:
    No lines \ frames data given: Last event time is the last photon time.
    Only lines data given: The last start-of-frame time is created, and the difference between subsequent frames
    in the data is added.
    Frames data exists: The last frame time plus the difference between subsequent frames is the last event time.
    :param dict_of_data: Dictionary of data.
    :param lines_per_frame: Lines per frame.
    :return: int
    """

    # Basic assertions
    if lines_per_frame < 1:
        raise ValueError('No lines per frame value received, or value was corrupt.')

    if 'PMT1' not in dict_of_data:
        raise ValueError('No PMT1 channel in dict_of_data.')

    ##
    if 'Frames' in dict_of_data:
        last_frame_time = dict_of_data['Frames'].loc[:, 'abs_time'].iloc[-1]
        if dict_of_data['Frames'].shape[0] == 1:
            return int(2 * last_frame_time)
        else:
            frame_diff = int(dict_of_data['Frames'].loc[:, 'abs_time'].diff().mean())
            return int(last_frame_time + frame_diff)

    if 'Lines' in dict_of_data:
        num_of_lines_recorded = dict_of_data['Lines'].shape[0]
        div, mod = divmod(num_of_lines_recorded, lines_per_frame)
        if num_of_lines_recorded > lines_per_frame * (div+1):  # excessive number of lines
            last_line_of_last_frame = dict_of_data['Lines'].loc[:, 'abs_time']\
                .iloc[div * lines_per_frame - 1]
            frame_diff = dict_of_data['Lines'].loc[:, 'abs_time'].iloc[div * lines_per_frame - 1] -\
                dict_of_data['Lines'].loc[:, 'abs_time'].iloc[(div - 1) * lines_per_frame]
            return int(last_line_of_last_frame + frame_diff)

        elif mod == 0:  # number of lines contained exactly in number of lines per frame
            return int(dict_of_data['Lines'].loc[:, 'abs_time'].iloc[-1] + dict_of_data['Lines']\
                .loc[:, 'abs_time'].diff().mean())

        elif num_of_lines_recorded < lines_per_frame * (div+1):
            missing_lines = lines_per_frame - mod
            line_diff = int(dict_of_data['Lines'].loc[:, 'abs_time'].diff().mean())
            return int(dict_of_data['Lines'].loc[:, 'abs_time'].iloc[-1] +\
                ((missing_lines+1) * line_diff))

    # Just PMT data
    max_pmt1 = dict_of_data['PMT1'].loc[:, 'abs_time'].max()
    try:
        max_pmt2 = dict_of_data['PMT2'].loc[:, 'abs_time'].max()
    except KeyError:
        return max_pmt1
    else:
        return max(max_pmt1, max_pmt2)

