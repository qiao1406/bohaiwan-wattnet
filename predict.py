from utils.config import Config
config_path = 'config.json'
conf = Config(config_path)

from dataset import get_data
from wattnet_predict import wattnet_predict
import utils.pred_utils as pu
from utils import data_process
from utils import draw_pic
from utils import metric


pred_res_dir = None

if __name__ == '__main__':
    # 存放预测结果文件的路径
    pred_target_filename = conf.predict_target
    x_train, y_train, x_test, y_test = get_data(pred_target_filename)
    pred = wattnet_predict(x_train, y_train, x_test)
    print('Process end.')
