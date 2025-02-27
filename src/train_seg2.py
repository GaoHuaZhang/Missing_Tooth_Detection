### Setup detectron2 logger
import detectron2
from detectron2.utils.logger import setup_logger
setup_logger()

### import some common libraries
import os
import numpy as np
import cv2
import random
import torch
import copy

### import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.data import detection_utils as utils
import detectron2.data.transforms as T
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.checkpoint import DetectionCheckpointer, Checkpointer
from detectron2.data import build_detection_test_loader, build_detection_train_loader
from detectron2.data.datasets import register_coco_instances

def custom_mapper2(dataset_dict):
    dataset_dict = copy.deepcopy(dataset_dict)  # it will be modified by code below
    image = utils.read_image(dataset_dict["file_name"], format='BGR')
    transform_list = [
        T.Resize((1000,2000))]
    image, transforms = T.apply_transform_gens(transform_list, image)
    dataset_dict["image"] = torch.as_tensor(image.transpose(2, 0, 1).astype("float32"))
    # dataset_dict["image"] = torch.as_tensor(image)

    annos = [
        utils.transform_instance_annotations(obj, transforms, image.shape[:2])
        for obj in dataset_dict.pop("annotations")
        if obj.get("iscrowd", 0) == 0
    ]
    instances = utils.annotations_to_instances(annos, image.shape[:2])
    dataset_dict["instances"] = utils.filter_empty_instances(instances)
    return dataset_dict

def custom_mapper(dataset_dict):
    dataset_dict = copy.deepcopy(dataset_dict)  # it will be modified by code below
    image = utils.read_image(dataset_dict["file_name"], format='BGR')
    transform_list = [
        T.Resize((1000,2000)),
        T.RandomBrightness(0.8, 1.2),
        T.RandomContrast(0.8, 1.2),
        T.RandomSaturation(0.8, 1.2)]
    image, transforms = T.apply_transform_gens(transform_list, image)
    dataset_dict["image"] = torch.as_tensor(image.transpose(2, 0, 1).astype("float32"))
    # dataset_dict["image"] = torch.as_tensor(image)

    annos = [
        utils.transform_instance_annotations(obj, transforms, image.shape[:2])
        for obj in dataset_dict.pop("annotations")
        if obj.get("iscrowd", 0) == 0
    ]
    instances = utils.annotations_to_instances(annos, image.shape[:2])
    dataset_dict["instances"] = utils.filter_empty_instances(instances)
    return dataset_dict

class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_train_loader(cls, cfg):
        return build_detection_train_loader(cfg, custom_mapper)
    def build_eval_loader(cls, cfg):
        return build_detection_test_loader(cfg, custom_mapper2) # 2
    def build_evaluator(cls, cfg):
        return COCOEvaluator(cfg.DATASETS.TEST,{"bbox","segm"},False,output_dir=cfg.OUTPUT_DIR)

def main():
    register_coco_instances("train_dataset", {}, "/SSD4/kyeongsoo/implant/Instance_Segmentation/train/coco_inst_teeth.json", "/SSD4/kyeongsoo/implant/Instance_Segmentation/train/")
    
    ### TRAINING
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
    cfg.DATASETS.TRAIN = ("train_dataset",)
    cfg.DATASETS.TEST = ()
    cfg.DATALOADER.NUM_WORKERS = 4

    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")  # Let training initialize from model zoo
    #cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "/SSD4/kyeongsoo/implant_code/output/lr_iter_10000BEST.pth") # 모델 가중치 불러오기
    cfg.SOLVER.IMS_PER_BATCH = 4
    cfg.SOLVER.BASE_LR = 0.0015  # pick a good LR
    cfg.SOLVER.MAX_ITER = 10000    # 300 iterations seems good enough for this toy dataset; you will need to train longer for a practical dataset
    cfg.SOLVER.STEPS = []        # do not decay learning rate

    # cfg.SOLVER.LR_SCHEDULER_NAME = "WarmupCosineLR"  # WarmupCosineLR  or WarmupMultiStepLR # 스케줄러

    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 512   # faster, and good enough for this toy dataset (default: 512)
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 28  
    cfg.OUTPUT_DIR = 'output/implantout'

    # cfg_file = yaml.safe_load(cfg.dump())
    # with open('configs/implant.yaml', 'w') as f:
    #     yaml.dump(cfg_file, f)

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    #trainer = DefaultTrainer(cfg) 
    trainer = CustomTrainer(cfg) 
    trainer.resume_or_load(resume=False)
    trainer.train()

    checkpointer = DetectionCheckpointer(trainer.model, save_dir="output")
    checkpointer.save("final_seg_10000")

main()

# 임의의 train 이미지를 불러온다.

#####################################################
# import random
# import matplotlib.pyplot as plt

# my_dataset_train_metadata = MetadataCatalog.get("train_dataset")
# dataset_dicts = DatasetCatalog.get("train_dataset")

# for d in random.sample(dataset_dicts, 4):
#     img = cv2.imread(d["file_name"])
#     v = Visualizer(img[:, :, ::-1], metadata=my_dataset_train_metadata, scale=0.5)
#     v = v.draw_dataset_dict(d)
#     cv2.imwrite('/SSD4/kyeongsoo/implant_code/trainv.jpg', v.get_image()[:, :, ::-1]) # 이미지 저장    

####################################################