#  Copyright (c) 2021, Tuan Nguyen.
#  All rights reserved.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from model import LAMDA

from layers import noise
from test_da_template_lamda import main_func, resolve_conflict_params

from tensorflow.python.layers.core import dropout
from tensorbayes.layers import dense, conv2d, avg_pool, max_pool

import warnings
import os
from generic_utils import tuid, model_dir
import signal
import sys
import time
import datetime
from pprint import pprint

choice_default = 1
warnings.simplefilter("ignore", category=DeprecationWarning)

model_name = "LAMDA-results"
current_time = tuid()


# generator
def encode_layout(preprocess, training_phase=True, cnn_size='large'):
    layout = []
    if cnn_size == 'small':
        layout = [
            (dense, (256,), {}),
            (dropout, (), dict(training=training_phase)),
            (noise, (1,), dict(phase=training_phase)),
        ]
    elif cnn_size == 'large':
        layout = [
            (preprocess, (), {}),
            (conv2d, (96, 3, 1), {}),
            (conv2d, (96, 3, 1), {}),
            (conv2d, (96, 3, 1), {}),
            (max_pool, (2, 2), {}),
            (dropout, (), dict(training=training_phase)),
            (noise, (1,), dict(phase=training_phase)),
            (conv2d, (192, 3, 1), {}),
            (conv2d, (192, 3, 1), {}),
            (conv2d, (192, 3, 1), {}),
            (max_pool, (2, 2), {}),
            (dropout, (), dict(training=training_phase)),
            (noise, (1,), dict(phase=training_phase)),
        ]
    return layout


def decode_layout(training_phase=True):
    layout = [
        (dense, (2048,), {}),
        (dropout, (), dict(training=training_phase)),
        (noise, (1,), dict(phase=training_phase)),
    ]
    return layout


# classifier
def class_discriminator_layout(num_classes=None, global_pool=True, activation=None, cnn_size='large'):
    layout = []
    if cnn_size == 'small':
        layout = [
            (dense, (num_classes,), dict(activation=activation))
        ]

    elif cnn_size == 'large':
        layout = [
            (conv2d, (192, 3, 1), {}),
            (conv2d, (192, 3, 1), {}),
            (conv2d, (192, 3, 1), {}),
            (avg_pool, (), dict(global_pool=global_pool)),
            (dense, (num_classes,), dict(activation=activation))
        ]
    return layout


# discriminator
def domain_layout(c):
    layout = [
        # (dense, (100,), {}),
        (dense, (c,), dict(activation=None))
    ]
    return layout


def create_obj_func(params):
    if len(sys.argv) > 1:
        my_choice = int(sys.argv[1])
    else:
        my_choice = choice_default
    if my_choice == 0:
        default_params = {
        }
    else:
        default_params = {
            'batch_size': 128,
            'learning_rate': 1e-4,
            'num_iters': 80000,
            'src_class_trade_off': 1.0,
            'domain_trade_off': 10.0,
            'src_vat_trade_off': 1.0,
            'trg_trade_off': 1.0,
            'm_on_D_trade_off': 1.0,
            'm_plus_1_on_D_trade_off': 1.0,
            'm_plus_1_on_G_trade_off': 1.0,
            'm_on_G_trade_off': 0.1,
            'src_recons_trade_off': 0.0,
            'lamda_model_id': '',
            'classify_layout': class_discriminator_layout,
            'encode_layout': encode_layout,
            'decode_layout': decode_layout,
            'domain_layout': domain_layout,
            'freq_calc_metrics': 10,
            'init_calc_metrics': -1,
            'log_path': os.path.join(model_dir(), model_name, "logs", "{}".format(current_time)),
            'summary_freq': 400,
            'current_time': current_time,
            'inorm': True,
            'save_grads': False,
            'cast_data': False,
            'only_save_final_model': True,
            'cnn_size': 'large',
            'update_target_loss': True,
            'data_augmentation': False,
        }

    default_params = resolve_conflict_params(params, default_params)

    print('Default parameters:')
    pprint(default_params)

    learner = LAMDA(
        **params,
        **default_params,
    )
    return learner


def main_test(run_exp=False):
    params_gridsearch = {
        'learning_rate': [1e-3, 1e-2],
    }
    attribute_names = (
        'learning_rate', 'same_network', 'src_class_trade_off', 'trg_trade_off',
        'src_vat_trade_off', 'domain_trade_off', 'adapt_domain_trade_off', 'num_iters', 'model_name')

    main_func(
        create_obj_func,
        choice_default=choice_default,
        src_name_default='mnist32_60_10',
        trg_name_default='mnistm32_60_10',
        params_gridsearch=params_gridsearch,
        attribute_names=attribute_names,
        num_workers=2,
        file_config=None,
        run_exp=run_exp,
        freq_predict_display=10,
        summary_freq=100,
        current_time=current_time,
        log_path=os.path.join(model_dir(), model_name, "logs", "{}".format(current_time))
    )

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.console_log_path = os.path.join(model_dir(), model_name, "console_output", "{}.txt".format(current_time))
        if not os.path.exists(os.path.dirname(self.console_log_path)):
            os.makedirs(os.path.dirname(self.console_log_path))
        self.log = open(self.console_log_path, 'a')
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        print('You pressed Ctrl+C.')
        self.log.close()

        # Remove logfile
        os.remove(self.console_log_path)
        print('Removed console_output file')
        sys.exit(0)

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass

if __name__ == '__main__':
    # pytest.main([__file__])
    sys.stdout = Logger()
    start_time = time.time()
    print('Running {} ...'.format(os.path.basename(__file__)))
    main_test(run_exp=True)
    training_time = time.time() - start_time
    print('Total time: %s' % str(datetime.timedelta(seconds=training_time)))
    print("============ LOG-ID: %s ============" % current_time)
