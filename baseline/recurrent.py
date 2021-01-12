import numpy as np
import torch
from torch import optim
from torch.utils.data import DataLoader, TensorDataset
from tqdm import trange
from utils.config import Config
from baseline.recurrent_fusion import RNNFusion, GRUFusion, LSTMFusion
from utils import normalization
from utils.metric import RMSELoss


conf = Config()
# 加载模型相关参数
num_workers, batch_size, epoch_num, learning_rate, save_model, load_model \
    = conf.get_config('recurrent-hyper-para',
                      inner_keys=['num-workers',
                                  'batch-size',
                                  'epoch-num',
                                  'learning-rate',
                                  'save-model',
                                  'load-model'
                                  ]
                      )
rnn_hidden_size = conf.get_config('recurrent-hyper-para', 'rnn-hidden-size')
gru_hidden_size = conf.get_config('recurrent-hyper-para', 'gru-hidden-size')
lstm_hidden_size = conf.get_config('recurrent-hyper-para', 'lstm-hidden-size')
# 选定运行的设备
if torch.cuda.is_available() and conf.get_config('device', 'use-gpu'):
    device = torch.device(conf.get_config('device', 'cuda'))
else:
    device = torch.device('cpu')
# 加载数据参数
pred_len, env_factor_num = conf.get_config('recurrent-hyper-para', inner_keys=['pred-len', 'env-factor-num'])
# 存放模型参数的路径
para_save_path = conf.get_config('model-weights-loc', 'local' if conf.get_config('run-on-local') else 'server')


def union_predict(model, x_train, y_train, x_test):
    """
    使用循环神经网络模型来进行联合预测
    @param model: 使用的具体模型
    @param x_train: 类型为 numpy 数组，形状为 m_train x (p + k)
    @param y_train: 类型为 numpy 数组，形状为 (m_train,)
    @param x_test: 类型为 numpy 数组，形状为 m_test x (p + k)
    @return: 预测结果，类型是 numpy 数组
    """
    # 加载数据
    data_loader, x_test = get_dataloader(x_train, y_train, x_test, normalize=False)

    if load_model:  # 加载已训练好的模型
        col = conf.get_config('predict-col')
        path = f'{para_save_path}/{col}_{model.name()}.pkl'
        model.load_state_dict(torch.load(path))
        print(f'从{path}处加载模型参数')
    else:  # 训练模型
        model = train_model(model, data_loader)

    # 将输出的结果进行处理并返回
    pred = model(x_test)
    pred = pred.data.to('cpu').numpy()
    pred = pred.reshape(-1)
    return pred


def lstm_union_predict(x_train, y_train, x_test):
    model = LSTMFusion(time_series_len=pred_len, input_feature=1).to(device)
    return union_predict(model, x_train, y_train, x_test)


def gru_union_predict(x_train, y_train, x_test):
    model = GRUFusion(time_series_len=pred_len, input_feature=1).to(device)
    return union_predict(model, x_train, y_train, x_test)


def rnn_union_predict(x_train, y_train, x_test):
    model = RNNFusion(time_series_len=pred_len, input_feature=1).to(device)
    return union_predict(model, x_train, y_train, x_test)


def train_model(model, data_loader):
    rmse = RMSELoss()
    opt = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=2, threshold=1e-3, min_lr=1e-6)
    min_loss = np.inf
    min_epoch = 0

    with trange(epoch_num) as t:

        for epoch in t:

            now_lr = opt.state_dict()['param_groups'][0]['lr']
            t.set_description(f'[e: {epoch}, lr:{now_lr}]')
            model.train()

            train_loss = 0.0
            for i, data in enumerate(data_loader):
                x, y = data

                with torch.set_grad_enabled(True):
                    pred_y = model(x)
                    loss = rmse(pred_y, y)
                    train_loss += loss.item() * len(x)

                    opt.zero_grad()
                    loss.backward()
                    opt.step()

            train_loss /= len(data_loader.dataset)
            if train_loss < min_loss:
                min_loss = train_loss
                min_epoch = epoch
            t.set_postfix(ml=min_loss, me=min_epoch)

            scheduler.step(loss)  # 更新学习率

    if save_model:  # 保存模型
        col = conf.get_config('predict-col')
        path = f'{para_save_path}/{col}_{model.name()}.pkl'
        torch.save(model.state_dict(), path)
        print(f'模型参数已存储到{path}')

    return model


def get_dataloader(x_train, y_train, x_test, normalize=True):
    normal = None
    if normalize:  # 归一化
        normal = normalization.MinMaxNormal(y_train)
        # x_train = normal.transform(x_train)
        y_train = normal.transform(y_train)
        # x_test = normal.transform(x_test)

    if x_train.ndim == 2:  # 改变形状格式, 使其变成三维的
        x_train = x_train.reshape(-1, 1, x_train.shape[1])
        x_test = x_test.reshape(-1, 1, x_test.shape[1])

    # 转换成 tensor
    x_train = torch.from_numpy(x_train).float().to(device)
    y_train = torch.from_numpy(y_train).float().to(device)
    x_test = torch.from_numpy(x_test).float().to(device)

    # 构建 DataSet 和 DataLoader
    dataset = TensorDataset(x_train, y_train)
    data_loader = DataLoader(dataset=dataset, shuffle=True, batch_size=batch_size, num_workers=num_workers)

    if normalize:
        return data_loader, x_test, normal
    else:
        return data_loader, x_test