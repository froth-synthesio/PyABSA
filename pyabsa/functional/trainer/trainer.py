# -*- coding: utf-8 -*-
# file: trainer.py
# time: 2021/4/22 0022
# author: yangheng <yangheng@m.scnu.edu.cn>
# github: https://github.com/yangheng95
# Copyright (C) 2021. All Rights Reserved.
import copy
import os

import findfile
import torch
import transformers

from pyabsa import __version__

from pyabsa.functional.dataset import DatasetItem
from pyabsa.functional.config.config_manager import ConfigManager
from pyabsa.functional.dataset import detect_dataset
from pyabsa.core.apc.prediction.sentiment_classifier import SentimentClassifier
from pyabsa.core.apc.training.apc_trainer import train4apc
from pyabsa.core.atepc.prediction.aspect_extractor import AspectExtractor
from pyabsa.core.atepc.training.atepc_trainer import train4atepc
from pyabsa.core.tc.prediction.text_classifier import TextClassifier
from pyabsa.core.tc.training.classifier_trainer import train4classification

from pyabsa.functional.config.apc_config_manager import APCConfigManager
from pyabsa.functional.checkpoint.checkpoint_manager import APCCheckpointManager
from pyabsa.functional.config.atepc_config_manager import ATEPCConfigManager
from pyabsa.functional.config.classification_config_manager import ClassificationConfigManager
from pyabsa.utils.file_utils import query_local_version

from pyabsa.utils.logger import get_logger

from pyabsa.utils.pyabsa_utils import get_device

import warnings

warnings.filterwarnings('once')


def init_config(config, auto_device):
    config.device, config.device_name = get_device(auto_device)
    config.auto_device = auto_device
    config.device = 'cuda' if auto_device == 'all_cuda' else config.device
    config.model_name = config.model.__name__.lower() if not isinstance(config.model, list) else 'ensemble'
    config.PyABSAVersion = __version__
    config.TransformersVersion = transformers.__version__
    config.TorchVersion = '{}+cuda{}'.format(torch.version.__version__, torch.version.cuda)

    if 'use_syntax_based_SRD' in config:
        print('-' * 130)
        print('Force to use syntax distance-based semantic-relative distance,'
              ' however Chinese is not supported to parse syntax distance yet!  ')
        print('-' * 130)
    return config


class Trainer:
    def __init__(self,
                 config: ConfigManager = None,
                 dataset=None,
                 from_checkpoint: str = None,
                 checkpoint_save_mode: int = 0,
                 auto_device=True,
                 path_to_save=None
                 ):
        """

        :param config: PyABSA.config.ConfigManager
        :param dataset: Dataset name, or a dataset_manager path, or a list of dataset_manager paths
        :param from_checkpoint: A checkpoint path to train based on
        :param checkpoint_save_mode: Save trained model to checkpoint,
                                     "checkpoint_save_mode=1" to save the state_dict,
                                     "checkpoint_save_mode=2" to save the whole model,
                                     "checkpoint_save_mode=3" to save the fine-tuned BERT,
                                     otherwise avoid saving checkpoint but return the trained model after training
        :param auto_device: True or False, otherwise 'allcuda', 'cuda:1', 'cpu' works

        """
        if not torch.cuda.device_count() > 1 and auto_device == 'allcuda':
            print('Cuda count <= 1, reset auto_device=True')
            auto_device = True
        config.ABSADatasetsVersion = query_local_version()
        if isinstance(config, APCConfigManager):
            self.train_func = train4apc
            self.model_class = SentimentClassifier
            self.task = 'apc'

        elif isinstance(config, ATEPCConfigManager):
            self.train_func = train4atepc
            self.model_class = AspectExtractor
            self.task = 'atepc'
        elif isinstance(config, ClassificationConfigManager):
            self.train_func = train4classification
            self.model_class = TextClassifier
            self.task = 'classification'

        self.config = config
        if isinstance(dataset, DatasetItem):
            self.config.dataset_item = list(dataset)
            self.config.dataset_name = dataset.dataset_name
        else:
            custom_dataset = DatasetItem('custom_dataset', dataset)
            self.config.dataset_item = list(custom_dataset)
            self.config.dataset_name = os.path.basename(custom_dataset.dataset_name)
        self.dataset_file = detect_dataset(dataset, task=self.task)
        self.config.dataset_file = self.dataset_file

        self.config = init_config(self.config, auto_device)

        self.from_checkpoint = findfile.find_dir(os.getcwd(), from_checkpoint) if from_checkpoint else ''
        self.checkpoint_save_mode = checkpoint_save_mode
        self.config.save_mode = checkpoint_save_mode
        log_name = self.config.model_name
        self.logger = get_logger(os.getcwd(), log_name=log_name, log_type='training')

        if checkpoint_save_mode or self.dataset_file['valid']:
            if path_to_save:
                config.model_path_to_save = path_to_save
            elif self.dataset_file['valid'] and not checkpoint_save_mode:
                print('Using Validation set needs to save checkpoint, turn on checkpoint-saving ...')
                config.model_path_to_save = 'checkpoints'
                self.config.save_mode = 1
            else:
                config.model_path_to_save = 'checkpoints'
        else:
            config.model_path_to_save = None

        self.inference_model = None
        self.model_path = None

    def train(self):
        """
        just return the trained model for inference (e.g., polarity classification, aspect-term extraction)
        """

        if isinstance(self.config.seed, int):
            self.config.seed = [self.config.seed]
        model_path = []
        seeds = self.config.seed
        model = None
        for i, s in enumerate(seeds):
            config = copy.deepcopy(self.config)
            config.seed = s
            if self.checkpoint_save_mode:
                model_path.append(self.train_func(config, self.from_checkpoint, self.logger))
            else:
                # always return the last trained model if dont save trained model
                model = self.model_class(model_arg=self.train_func(config, self.from_checkpoint, self.logger))
        while self.logger.handlers:
            self.logger.removeHandler(self.logger.handlers[0])

        if self.checkpoint_save_mode:
            if os.path.exists(max(model_path)):
                self.inference_model = self.model_class(max(model_path))
                self.model_path = max(model_path)
        else:
            self.inference_model = model

    def load_trained_model(self):
        self.inference_model.to(self.config.device)
        return self.inference_model


class APCTrainer(Trainer):
    pass


class ATEPCTrainer(Trainer):
    pass


class TextClassificationTrainer(Trainer):
    pass
