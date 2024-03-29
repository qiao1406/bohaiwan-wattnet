import os
import pandas as pd
from utils import normalization


def split_date(frame):
    # 按日期分割，从缺失的日期处截断
    res, now = list(), list()
    for day in pd.date_range(frame.index[0], frame.index[-1], freq='D'):
        if day not in frame.index:
            if len(now) > 0:
                res.append(now)
            now = list()
        else:
            now.append(day)
    else:  # 最后剩的没有断的那一条连续日期
        if len(now) > 0:
            res.append(now)

    return res


def dump_csv(dirname, filename, data, average_func=None):
    """
    把统计结果的 DataFrame 写到 CSV 文件中
    :param dirname: 路径名
    :param filename: 写入的文件名
    :param data: 写入的数据，格式为 List[dict]
    :param average_func: 求均值的方法
    """

    if not os.path.exists(dirname):
        os.makedirs(dirname)

    df = pd.DataFrame(data)
    filename = os.path.join(dirname, filename)
    df.to_csv(filename, index=False)
    print('完成预测，已写入', filename)

    if average_func:
        average_metric(df, average_func)

    print()


def average_metric(data, average_func):
    """
    输出指标数据的平均值
    :param data: 指标数据，格式为 List[dict] 或 DataFrame
    :param average_func: 求均值的方法
    """
    # 转换格式
    df = pd.DataFrame(data) if type(data) is list else data

    # 统计总体的平均 RMSE, MAE 和 PCC
    print('RMSE', average_func(df.loc[:, 'RMSE']))
    print('MAE', average_func(df.loc[:, 'MAE']))
    print('MAPE', average_func(df.loc[:, 'MAPE']))
    print('PCC', average_func(df.loc[:, 'PCC']))
    print()


def dump_pred_res(dirname, filename, y, pred, sensor_name):
    """
    把预测得到的数据和真实数据写入到 CSV 文件中
    :param dirname: 存放文件的目录
    :param filename: 存放数据的文件名
    :param y: 真实值
    :param pred: 预测值
    :param sensor_name: 传感器名字的列表
    """

    data = {}
    for i in range(y.shape[2]):
        data[f'truth-{sensor_name[i]}'] = y[:, 0, i]
        data[f'pred-{sensor_name[i]}'] = pred[:, 0, i]
    df = pd.DataFrame(data)

    if not os.path.exists(dirname):
        os.makedirs(dirname)
    df.to_csv(os.path.join(dirname, filename))


def avg(series):
    """
    计算一个序列的平均值
    :param series: 序列，格式为 pandas.Series
    :return: 把空值去掉之后的平均值
    """
    series = series.dropna()
    avg_val = sum([float(i) for i in series]) / len(series)
    return round(avg_val, 4)


def section_normalization(data):
    """
    对样本集的每一个传感器进行归一化
    :param data: 类型为 numpy 数组，形状为 (m, pred_len, sensor_num)
    :return: 归一化后的样本集
    """
    return section_normalization_with_normalizer(data)[0]


def section_normalization_with_normalizer(data):
    """
    对样本集的每一个传感器进行归一化
    :param data: 类型为 numpy 数组, 形状为 (m, pred_len, sensor_num)
    :return: 归一化后的样本集和各个传感器的 normalizers
    """
    normalizers = []
    for i in range(data.shape[2]):
        x = data[:, :, i]
        normal_x = normalization.MinMaxNormal(x)
        data[:, :, i] = normal_x.transform(x)
        normalizers.append(normal_x)

    return data, normalizers


def reverse_section_normalization(data, normalizer):
    for i in range(data.shape[2]):
        data[:, :, i] = normalizer[i].inverse_transform(data[:, :, i])

    return data
