# PPIN
This repository is for the approach proposed in the paper *PPIN*.

- `./src` contains the implementation code of *PPIN*.
- `./trained_model` contains pre-trained models of PPIN.
- `./label` contains node-level labels used in PPIN.

## Prerequisites
```
conda create -n ppin python=3.9
conda activate ppin
conda install scikit-learn==1.2.0
pip install networkx==2.8.7
pip install xxhash==3.2.0
conda install graphviz==0.20.1

# PyTorch GPU version
conda install pytorch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1 pytorch-cuda=11.8 -c pytorch -c nvidia
pip install torch_geometric==2.0.0
pip install pyg_lib torch_scatter torch_sparse torch_cluster torch_spline_conv

```

## Datasets preparation
DARPA Transparent Computing Engagement 3

E3-THEIA and E3-CADETS. Due to space constraints, we include only preprocessed datasets in the `data/` folder. You can unzip the corresponding `.zip` file to get json format files. Or you can preprocess these datasets from scratch as follows:
- Download raw data from [DARPA TC](https://github.com/darpa-i2o/Transparent-Computing).
    - Download all files for E3-CADETS in the [google drive](https://drive.google.com/drive/folders/179uDuz62Aw61Ehft6MoJCpPeBEz16VFy) and upzip into `{file_path}=/root/cadets3/`
    - Download all files for E3-THEIA in the [google drive](https://drive.google.com/drive/folders/1AWXy7GFGJWeJPGzvkT935kTfwBYzjhfC) and upzip into `{file_path}=/root/theia3/`

- Preprocess downloaded data.
    - Go to `./data` folder
    - run `preprocess_cadets3.py` to generate daily split json files for E3-CADETS
    - run `preprocess_theia3.py` to generate daily split json files for E3-THEIA

DARPA OPTC

Host 0201, 0501, 0051. We include preprocessed datasets in `data/optc.zip`


## Evaluation
- We provide pre-generated whitelist under `~/data/{dataname}`, unzipped from `{dataname}.zip`. Or you can generate it by running `python prepare.py {dataname}`. Valid choices of `{dataname}` are theia3 and cadets3.
---
- DARPA TC: Run `darpa_tc.py {dataname} {device}` to test on `theia3` or `cadets3` day by day.
- OPTC: Run `optc.py {hostid} {device}` to test on `0201`, `0501`, or `0051`.

- The output will be in `./result/{data_name}/`. Each subdirectory contains alerts per day/host including visualization graphs and node-level logs.
---
- Additionally, you can use `statistics.ipynb` to evaluate the node-level performance. We have released the detection results in `./result`, you can have a quick check just skipping the above steps.

## Reference
- https://github.com/threaTrace-detector/threaTrace
- https://github.com/ubc-provenance/kairos
- https://github.com/PKU-ASAL/Simulated-Data