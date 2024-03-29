from utils.config import Config

config_path = 'config.json'
conf = Config(config_path)

import time
from dataset import get_data
from utils import data_process
from utils import draw_pic
from utils import metric
from baseline.lr import lr_multiple_predict, lr_pca_predict
from baseline.svr import svr_multiple_predict
from baseline.mlp import mlp_multiple_predict, mlp_pca_predict
from baseline.recurrent import rnn_seq_predict, gru_seq_predict, lstm_seq_predict


if __name__ == '__main__':
    pred_target_filename = conf.predict_target
    pred_func = lstm_seq_predict
    sensor_name = conf.get_config('data-parameters', 'valid-sensors')
    x_train, y_train, x_test, y_test, normal_y = get_data(pred_target_filename, 'nanjing', valid_set=False)
    pred = pred_func(x_train, y_train, x_test)
    pred = data_process.reverse_section_normalization(pred, normal_y)
    y_test = data_process.reverse_section_normalization(y_test, normal_y)
    # 输出预测指标
    metrics = metric.metric_for_each_sensor(y_test, pred, sensor_name)
    # 存储预测结果
    now_time = time.strftime('%Y-%m-%d-%H-%M-%S')
    data_process.dump_csv(dirname='pred_res/metrics',
                          filename=now_time + '_' + pred_func.__name__ + '.csv',
                          data=metrics,
                          average_func=data_process.avg
                          )
    data_process.dump_pred_res(dirname=conf.get_config('predict-res-table', conf.run_location),
                               filename=time.strftime('%Y-%m-%d-%H-%M-%S') + '_' + pred_func.__name__ + '.csv',
                               y=y_test,
                               pred=pred,
                               sensor_name=sensor_name
                               )
