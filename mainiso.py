import torch
import utility
import loss
torch.backends.cudnn.enabled = False
import argparse
from div2k import Flouresceneiso
from trainer import Trainer
from torch.utils.data import dataloader
import model


def options():
    parser = argparse.ArgumentParser(description='EDSR and MDSR')
    parser.add_argument('--model', default=modelname, help='model name')
    parser.add_argument('--test_only', action='store_true', default=test_only,
                        help='set this option to test the model')
    parser.add_argument('--modelpath', type=str, default=modelpath, help='ENLCAx4.pt  pre-trained model directory')
    parser.add_argument('--task', type=int, default=3)

    parser.add_argument('--inputchannel', type=int, default=1, help='')
    scale = 1
    parser.add_argument('--resume', type=int, default=resume, help='-2:best;-1:latest.ptb; 0:pretrain; >0: resume')
    parser.add_argument('--save', type=str, default=savepath, help='% (SwinIR, testset),')
    
    # Data specifications
    parser.add_argument('--data_test', type=str, default=testset, help='demo image directory')
    parser.add_argument('--epochs', type=int, default=1000, help='number of epochs to train')
    parser.add_argument('--rgb_range', type=int, default=1, help='maximum value of RGBn_colors')
    parser.add_argument('--n_colors', type=int, default=1, help='')
    parser.add_argument('--datamin', type=int, default=0)
    parser.add_argument('--datamax', type=int, default=100)
    parser.add_argument('--condition', type=int, default=condition)

    parser.add_argument('--batch_size', type=int, default=batchsize, help='input batch size for training')
    parser.add_argument('--cpu', action='store_true', default=False, help='')
    parser.add_argument('--print_every', type=int, default=400,
                        help='how many batches to wait before logging training status')
    parser.add_argument('--test_every', type=int, default=3000,
                        help='how many batches to save models')
        
    parser.add_argument('--patch_size', type=int, default=patch_size, help='input batch size for training')
    parser.add_argument('--n_GPUs', type=int, default=1, help='number of GPUs')
    
    parser.add_argument('--chop', action='store_true', default=True, help='enable memory-efficient forward')
    parser.add_argument('--pre_train', type=str, default=modelpath, help='pre-trained model directory')
    parser.add_argument('--load', type=str, default='', help='file name to load')
    parser.add_argument('--debug', action='store_true', help='Enables debug mode')

    parser.add_argument('--scale', type=str, default='%d' % scale,
                        help='super resolution scale')
    parser.add_argument('--chunk_size', type=int, default=144,
                        help='attention bucket size')
    parser.add_argument('--n_hashes', type=int, default=4,
                        help='number of hash rounds')
    # Model specifications
    parser.add_argument('--extend', type=str, default='.', help='pre-trained model directory')
    parser.add_argument('--shift_mean', default=True, help='subtract pixel mean from the input')
    parser.add_argument('--precision', type=str, default='single',
                        choices=('single', 'half'), help='FP precision for test (single | half)')

    parser.add_argument('--seed', type=int, default=1, help='random seed')
    parser.add_argument('--local_rank', type=int, default=0)

    # Hardware specifications
    parser.add_argument('--n_threads', type=int, default=0, help='number of threads for data loading')
    # Training specifications
    parser.add_argument('--reset', action='store_true', help='reset the training')
    parser.add_argument('--split_batch', type=int, default=1,
                        help='split the batch into smaller chunks')
    parser.add_argument('--self_ensemble', action='store_true',
                        help='use self-ensemble method for test')
    
    # Optimization specifications
    parser.add_argument('--lr', type=float, default=1e-4,
                        help='learning rate')
    parser.add_argument('--decay', type=str, default='200',
                        help='learning rate decay type')
    parser.add_argument('--gamma', type=float, default=0.5,
                        help='learning rate decay factor for step decay')
    parser.add_argument('--optimizer', default='ADAM',
                        choices=('SGD', 'ADAM', 'RMSprop'),
                        help='optimizer to use (SGD | ADAM | RMSprop)')
    parser.add_argument('--momentum', type=float, default=0.9,
                        help='SGD momentum')
    parser.add_argument('--betas', type=tuple, default=(0.9, 0.999),
                        help='ADAM beta')
    parser.add_argument('--epsilon', type=float, default=1e-8,
                        help='ADAM epsilon for numerical stability')
    parser.add_argument('--weight_decay', type=float, default=0,
                        help='weight decay')
    parser.add_argument('--gclip', type=float, default=0,
                        help='gradient clipping threshold (0 = no clipping)')
    
    # Loss specifications
    parser.add_argument('--loss', type=str, default='1*L1',
                        help='loss function configuration')
    parser.add_argument('--skip_threshold', type=float, default='1e8',
                        help='skipping batch that has large error')
    
    # Log specifications
    parser.add_argument('--save_models', action='store_true', default=True,
                        help='save all intermediate models')
    parser.add_argument('--save_results', action='store_true', default=True,
                        help='save output results')
    
    args = parser.parse_args()
    
    args.scale = list(map(lambda x: int(x), args.scale.split('+')))
    
    for arg in vars(args):
        if vars(args)[arg] == 'True':
            vars(args)[arg] = True
        elif vars(args)[arg] == 'False':
            vars(args)[arg] = False
    
    return args


def main():
    loader_test = [dataloader.DataLoader(
        Flouresceneiso(args, istrain=False),
        batch_size=1,
        shuffle=False,
        pin_memory=not args.cpu,
        num_workers=args.n_threads,
    )]
    if not args.test_only:
        loader_train = dataloader.DataLoader(
            Flouresceneiso(args, istrain=True),
            batch_size=args.batch_size,
            shuffle=True,
            pin_memory=not args.cpu,
            num_workers=0,
        )
    else:
        loader_train = None
        
    _model = model.Model(args, checkpoint)
    _loss = loss.Loss(args, checkpoint) if not args.test_only else None
    t = Trainer(args, loader_train, loader_test, args.data_test, _model, _loss, checkpoint)

    if test_only:
        t.testiso_rotate()
    else:
        while t.terminate():
            t.train()
    
    checkpoint.done()


if __name__ == '__main__':
    modelname = 'SwinIR'
    testsetlst = ['Isotropic_Liver']  #
    test_only = True  # False  #
    normrange = 'Norm_0-100'  #
    batchsize = 6

    resume = -465
    patch_size = 128
    datamin, datamax = 0, 100
    condition = 1
    for testset in testsetlst:
        savepath = '%s%s/' % (modelname, testset)
        modelpath = './experiment/%s/model_best.pt' % savepath
        args = options()
        torch.manual_seed(args.seed)
        checkpoint = utility.checkpoint(args)
        main()
