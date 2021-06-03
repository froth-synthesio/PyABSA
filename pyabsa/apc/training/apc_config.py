model_name = "slide_lcfs_bert"
optimizer = "adam"
learning_rate = 0.00002
pretrained_bert_name = "bert-base-uncased"
use_dual_bert = False
use_bert_spc = True
max_seq_len = 80
SRD = 3
sigma = 0.3
lcf = "cdw"
window = "lr"
eta = -1
dropout = 0
l2reg = 0.00001
num_epoch = 3
batch_size = 16
initializer = 'xavier_uniform_'
seed = 996
embed_dim = 768
hidden_dim = 768
polarities_dim = 3
log_step = 3
dynamic_truncate = True
