# DASH: Warm-Starting Neural Network Training Without Loss of Plasticity Under Stationarity

This repository contains the implementation of Direction-Aware SHrinking (DASH), a method for warm-starting neural network training without losing plasticity under stationary conditions.

## 📄 Paper

For more details, check out our paper: 

[DASH: Warm-Starting Neural Network Training Without Loss of Plasticity Under Stationarity](https://openreview.net/pdf?id=GR5LXaglgG)

## 🛠️ Setup

To set up the environment, run:

```
conda env create -f env.yaml
```

## 🚀 Usage

### Basic Training

To train the model, use:

```
python main.py --dataset [dataset] --train_type [type]
```

Available options:
- Datasets: `cifar10`, `cifar100`, `svhn`, `imagenet`
- Training types: `cold`, `warm`, `warm_rm`, `reset`, `l2_init`, `sp`, `dash`

### Training on Tiny-ImageNet

## 📚 Citation
```bibtex
@inproceedings{
    shin2024dash,
    title={{DASH}: Warm-Starting Neural Network Training Without Loss of Plasticity Under Stationarity},
    author={Baekrok Shin and Junsoo Oh and Hanseul Cho and Chulhee Yun},
    booktitle={2nd Workshop on Advancing Neural Network Training: Computational Efficiency, Scalability, and Resource Optimization (WANT@ICML 2024)},
    year={2024},
    url={https://openreview.net/forum?id=GR5LXaglgG}
}
```
