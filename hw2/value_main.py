import argparse
import os
import random
import shutil
import time
import warnings
import re
from enum import Enum

import torch
import torch.backends.cudnn as cudnn
import torch.distributed as dist
import torch.multiprocessing as mp
import torch.nn as nn
import torch.nn.parallel
import torch.optim
import torch.utils.data
import torch.utils.data.distributed
import torchvision.datasets as datasets
import torchvision.models as models
import torchvision.transforms as transforms
from torch.optim.lr_scheduler import StepLR
from torch.utils.data import Subset
from torch.utils.tensorboard import SummaryWriter

model_names = sorted(name for name in models.__dict__
                     if name.islower() and not name.startswith("__")
                     and callable(models.__dict__[name]))

parser = argparse.ArgumentParser(description='PyTorch ImageNet Training')
parser.add_argument('data', metavar='DIR', nargs='?', default='tiny-imagenet-200',
                    help='path to dataset (default: imagenet)')  # 目录
parser.add_argument('-a', '--arch', metavar='ARCH', default='resnet18',
                    choices=model_names,
                    help='model architecture: ' +
                         ' | '.join(model_names) +
                         ' (default: resnet18)')  # 模型
parser.add_argument('-j', '--workers', default=4, type=int, metavar='N',
                    help='number of data loading workers (default: 4)')  # 训练过程中用于加载数据的并行工作线程数量
parser.add_argument('--epochs', default=90, type=int, metavar='N',
                    help='number of total epochs to run')  # 神经网络时要运行的总迭代次数
parser.add_argument('--start-epoch', default=0, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')  # 在重新开始训练时，手动指定的起始迭代次数。
parser.add_argument('-b', '--batch-size', default=256, type=int,
                    metavar='N',
                    help='mini-batch size (default: 256), this is the total '
                         'batch size of all GPUs on the current node when '
                         'using Data Parallel or Distributed Data Parallel')  # mini-batch size（小批量大小）指的是每个小批量中包含的样本数量。
parser.add_argument('--lr', '--learning-rate', default=0.1, type=float,
                    metavar='LR', help='initial learning rate', dest='lr')  # 学习率
parser.add_argument('--momentum', default=0.9, type=float, metavar='M',
                    help='momentum')  # 用动量参数来控制前一次更新的影响程度。
parser.add_argument('--wd', '--weight-decay', default=1e-4, type=float,
                    metavar='W', help='weight decay (default: 1e-4)',
                    dest='weight_decay')  # 权重衰减通过向损失函数中添加一个正则化项，惩罚较大的权重值，以促使模型学习到更简单和更平滑的权重分布
parser.add_argument('-p', '--print-freq', default=10, type=int,
                    metavar='N', help='print frequency (default: 10)')  # 在训练过程中定期输出或打印训练相关信息的频率
parser.add_argument('--resume', default='', type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')  # 在训练中断或需要重新开始训练时保留模型的当前状态，可以定期保存模型的检查点
parser.add_argument('-e', '--evaluate', dest='evaluate', action='store_true',
                    help='evaluate model on validation set')  # 在训练过程中使用验证集对模型进行评估
parser.add_argument('--pretrained', dest='pretrained', action='store_true',
                    help='use pre-trained model')  # 在机器学习或深度学习任务中使用预训练模型
parser.add_argument('--world-size', default=-1, type=int,
                    help='number of nodes for distributed training')
parser.add_argument('--rank', default=-1, type=int,
                    help='node rank for distributed training')
parser.add_argument('--dist-url', default='tcp://224.66.41.62:23456', type=str,
                    help='url used to set up distributed training')
parser.add_argument('--dist-backend', default='nccl', type=str,
                    help='distributed backend')  # 分布式后端提供了实现分布式训练的功能和工具
parser.add_argument('--seed', default=None, type=int,
                    help='seed for initializing training. ')
parser.add_argument('--gpu', default=None, type=int,
                    help='GPU id to use.')
parser.add_argument('--multiprocessing-distributed', action='store_true',
                    help='Use multi-processing distributed training to launch '
                         'N processes per node, which has N GPUs. This is the '
                         'fastest way to use PyTorch for either single node or '
                         'multi node data parallel training')  # 使用多进程分布式训练来在每个节点上启动N个进程
parser.add_argument('--dummy', action='store_true',
                    help="use fake data to benchmark")  # 使用虚拟数据进行基准测试 基准测试是评估算法、模型或系统性能的一种方法

best_acc1 = 0
output_dir = os.path.join("..", "output", "logs", "runs")
writer = SummaryWriter(output_dir)


def main():
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
        torch.manual_seed(args.seed)
        cudnn.deterministic = True  # 确定性计算，同一种子得到相同结果
        cudnn.benchmark = False  # 自动寻找最适合当前硬件的卷积实现配置的标志
        warnings.warn('You have chosen to seed training. '
                      'This will turn on the CUDNN deterministic setting, '
                      'which can slow down your training considerably! '
                      'You may see unexpected behavior when restarting '
                      'from checkpoints.')

    if args.gpu is not None:
        warnings.warn('You have chosen a specific GPU. This will completely '
                      'disable data parallelism.')

    if args.dist_url == "env://" and args.world_size == -1:  # 使用环境变量来动态配置进程数量
        args.world_size = int(os.environ["WORLD_SIZE"])

    args.distributed = args.world_size > 1 or args.multiprocessing_distributed  # 进程数量大于1或根据设置 进行分布式训练

    if torch.cuda.is_available():
        ngpus_per_node = torch.cuda.device_count()  # 检查当前系统是否支持CUDA，
    else:
        ngpus_per_node = 1
    if args.multiprocessing_distributed:
        # Since we have ngpus_per_node processes per node, the total world_size
        # needs to be adjusted accordingly
        args.world_size = ngpus_per_node * args.world_size  # 总的训练进程数量需要乘以每个节点上的GPU数量。
        # Use torch.multiprocessing.spawn to launch distributed processes: the
        # main_worker process function
        mp.spawn(main_worker, nprocs=ngpus_per_node, args=(ngpus_per_node, args))  # 启动！
    else:
        # Simply call main_worker function
        main_worker(args.gpu, ngpus_per_node, args)


def main_worker(gpu, ngpus_per_node, args):  # 主要训练函数
    global best_acc1
    global writer

    args.gpu = gpu

    if args.gpu is not None:
        print("Use GPU: {} for training".format(args.gpu))

    if args.distributed:
        if args.dist_url == "env://" and args.rank == -1:
            args.rank = int(os.environ["RANK"])
        if args.multiprocessing_distributed:
            # For multiprocessing distributed training, rank needs to be the
            # global rank among all the processes
            args.rank = args.rank * ngpus_per_node + gpu  # 全局排名统一 以便进行进程间的通信和同步
        dist.init_process_group(backend=args.dist_backend, init_method=args.dist_url,
                                world_size=args.world_size, rank=args.rank)
    # create model
    if args.pretrained:
        print("=> using pre-trained model '{}'".format(args.arch))
        model = models.__dict__[args.arch](pretrained=True)
    else:
        print("=> creating model '{}'".format(args.arch))
        model = models.__dict__[args.arch]()

    if not torch.cuda.is_available() and not torch.backends.mps.is_available():  # 后者检查系统是否支持CUDA的多进程模式（MPS）
        print('using CPU, this will be slow')
    elif args.distributed:
        # For multiprocessing distributed, DistributedDataParallel constructor
        # should always set the single device scope, otherwise, 确保构造函数中设置了单个设备范围
        # DistributedDataParallel will use all available devices.
        if torch.cuda.is_available():
            if args.gpu is not None:
                torch.cuda.set_device(args.gpu)
                model.cuda(args.gpu)  # 将模型移动到指定的GPU设备上
                # When using a single GPU per process and per
                # DistributedDataParallel, we need to divide the batch size
                # ourselves based on the total number of GPUs of the current node.
                args.batch_size = int(args.batch_size / ngpus_per_node)
                args.workers = int((args.workers + ngpus_per_node - 1) / ngpus_per_node)
                model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[args.gpu])  # 对模型进行封装
            else:
                model.cuda()
                # DistributedDataParallel will divide and allocate batch_size to all
                # available GPUs if device_ids are not set
                model = torch.nn.parallel.DistributedDataParallel(model)
    elif args.gpu is not None and torch.cuda.is_available():  # 非分布式，指定gpu
        torch.cuda.set_device(args.gpu)
        model = model.cuda(args.gpu)
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        model = model.to(device)
    else:
        # DataParallel will divide and allocate batch_size to all available GPUs
        if args.arch.startswith('alexnet') or args.arch.startswith('vgg'):
            model.features = torch.nn.DataParallel(model.features)
            model.cuda()
        else:
            model = torch.nn.DataParallel(model).cuda()

    if torch.cuda.is_available():
        if args.gpu:
            device = torch.device('cuda:{}'.format(args.gpu))
        else:  # 没指定的话默认为第一个
            device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    # define loss function (criterion), optimizer, and learning rate scheduler
    criterion = nn.CrossEntropyLoss().to(device)  # 创建一个交叉熵损失函数对象并将其移动到指定的设备上进行计算

    optimizer = torch.optim.SGD(model.parameters(), args.lr,
                                momentum=args.momentum,
                                weight_decay=args.weight_decay)  # 随机梯度下降优化器

    """Sets the learning rate to the initial LR decayed by 10 every 30 epochs"""
    scheduler = StepLR(optimizer, step_size=30, gamma=0.1)  # 学习率调度器，按照给定的步长（step_size）和衰减因子（gamma）来调整学习率。

    # optionally resume from a checkpoint
    if args.resume:  # 从检查点恢复
        if os.path.isfile(args.resume):
            print("=> loading checkpoint '{}'".format(args.resume))
            if args.gpu is None:
                checkpoint = torch.load(args.resume)
            elif torch.cuda.is_available():
                # Map model to be loaded to specified single gpu.
                loc = 'cuda:{}'.format(args.gpu)
                checkpoint = torch.load(args.resume, map_location=loc)
            args.start_epoch = checkpoint['epoch']
            best_acc1 = checkpoint['best_acc1']
            if args.gpu is not None:
                # best_acc1 may be from a checkpoint from a different GPU
                best_acc1 = best_acc1.to(args.gpu)
            model.load_state_dict(checkpoint['state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer'])
            scheduler.load_state_dict(checkpoint['scheduler'])
            print("=> loaded checkpoint '{}' (epoch {})"
                  .format(args.resume, checkpoint['epoch']))
        else:
            print("=> no checkpoint found at '{}'".format(args.resume))

    # Data loading code
    if args.dummy:  # 是否用虚拟数据集
        print("=> Dummy data is used!")
        train_dataset = datasets.FakeData(1281167, (3, 224, 224), 200, transforms.ToTensor())
        val_dataset = datasets.FakeData(50000, (3, 224, 224), 200, transforms.ToTensor())
    else:  # 导入数据
        traindir = os.path.join(args.data, 'train')  # 训练集
        valdir = os.path.join(args.data, 'val')  # 验证集
        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                         std=[0.229, 0.224, 0.225])  # 正则化

        train_dataset = datasets.ImageFolder(  #
            traindir,
            transforms.Compose([
                transforms.RandomHorizontalFlip(),  # 水平反转
                transforms.ToTensor(),  # 转化为张量
                normalize,
            ]))

        val_dataset = datasets.ImageFolder(
            valdir,
            transforms.Compose([
                transforms.ToTensor(),
                normalize,
            ]))
        val_dataset.classes = train_dataset.classes
        tag_list = []
        val_annodir = os.path.join(args.data, 'val')
        val_annodir = os.path.join(val_annodir, 'val_annotations.txt')
        with open(val_annodir, 'r') as file:
            content = file.read()
            words = content.split()
            times = 0
            for word in words:
                if times % 6 == 1:
                    tag_list.append(word)
                times += 1
        i = 0
        for img_name in val_dataset.imgs:
            pic_name = val_dataset.imgs[i][0]
            pic_num = os.path.basename(pic_name)
            pic_num = pic_num[4:]
            pic_num = ''.join(c for c in pic_num if c.isdigit())
            pic_num = int(pic_num)
            tag_num = train_dataset.classes.index(tag_list[pic_num])
            tag_tuple = (pic_name, tag_num)
            val_dataset.imgs[i] = tag_tuple
            val_dataset.targets[i] = tag_num
            i = i + 1
    if args.distributed:
        train_sampler = torch.utils.data.distributed.DistributedSampler(train_dataset)  # 分布式采样器
        val_sampler = torch.utils.data.distributed.DistributedSampler(val_dataset, shuffle=False,
                                                                      drop_last=True)  # 不洗牌 丢最后一个不构成一组的批次
    else:
        train_sampler = None
        val_sampler = None

    train_loader = torch.utils.data.DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=(train_sampler is None),
        num_workers=args.workers, pin_memory=True, sampler=train_sampler)  # 分布式进行洗牌

    val_loader = torch.utils.data.DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=True, sampler=val_sampler)

    dataiter = iter(train_loader)
    images, labels = next(dataiter)
    writer.add_graph(model, images)
    writer.flush()
    if args.evaluate:  # 评估模式
        validate(val_loader, model, criterion, args)
        return

    start = time.time()
    for epoch in range(args.start_epoch, args.epochs):  # 轮次 确保每个进程在每个轮次中使用不同的数据划分
        if args.distributed:
            train_sampler.set_epoch(epoch)  # 设置新的数据划分

        # train for one epoch
        train(train_loader, model, criterion, optimizer, epoch, device, args)  # 每轮的训练函数

        # evaluate on validation set
        acc1 = validate(val_loader, model, criterion, args, epoch)  # 每轮的评估值
        print("total train time : {} s".format(time.time()-start))
        writer.add_scalar('training time', time.time()-start, epoch)

        scheduler.step()  # 更新当前的学习率

        # remember best acc@1 and save checkpoint
        is_best = acc1 > best_acc1
        best_acc1 = max(acc1, best_acc1)

        if not args.multiprocessing_distributed or (args.multiprocessing_distributed  # 保存
                                                    and args.rank % ngpus_per_node == 0):
            save_checkpoint({
                'epoch': epoch + 1,
                'arch': args.arch,
                'state_dict': model.state_dict(),
                'best_acc1': best_acc1,
                'optimizer': optimizer.state_dict(),
                'scheduler': scheduler.state_dict()
            }, is_best)


def train(train_loader, model, criterion, optimizer, epoch, device, args):
    batch_time = AverageMeter('Time', ':6.3f')  # 统计各项指标
    data_time = AverageMeter('Data', ':6.3f')
    losses = AverageMeter('Loss', ':.4e')
    top1 = AverageMeter('Acc@1', ':6.2f')
    top5 = AverageMeter('Acc@5', ':6.2f')
    progress = ProgressMeter(  # 进度条
        len(train_loader),
        [batch_time, data_time, losses, top1, top5],
        prefix="Epoch: [{}]".format(epoch))

    # switch to train mode
    model.train()

    end = time.time()
    running_loss = 0.0
    running_accu = 0.0

    for i, (images, target) in enumerate(train_loader):
        # measure data loading time
        data_time.update(time.time() - end)  # 统计数据加载时间

        # move data to the same device as model
        images = images.to(device, non_blocking=True)  # 移动到对应设备
        target = target.to(device, non_blocking=True)

        # compute output
        output = model(images)
        loss = criterion(output, target)

        # measure accuracy and record loss
        acc1, acc5 = accuracy(output, target, topk=(1, 5))
        losses.update(loss.item(), images.size(0))  # 更新平均损失值
        top1.update(acc1[0], images.size(0))
        top5.update(acc5[0], images.size(0))

        # compute gradient and do SGD step
        optimizer.zero_grad()  # 缓存清零
        loss.backward()  # 反向传播计算梯度
        optimizer.step()  # 更新模型

        running_accu += acc5[0]
        running_loss += loss.item()
        if i % 100 == 99:
            writer.add_scalar('training loss',
                              running_loss / 100,
                              epoch * len(train_loader) + i)
            writer.add_scalar('training acc',
                              running_accu / 100,
                              epoch * len(train_loader) + i)
            writer.flush()
            running_loss = 0.0
            running_accu = 0.0

        # measure elapsed time
        batch_time.update(time.time() - end)  # 更新时间
        end = time.time()

        if i % args.print_freq == 0:
            progress.display(i + 1)  # 打印


def validate(val_loader, model, criterion, args, epoch=0):
    def run_validate(loader, base_progress=0):
        with torch.no_grad():
            end = time.time()
            running_loss = 0.0
            running_accu = 0.0
            wrong_file = []
            for i, (images, target) in enumerate(loader):
                i = base_progress + i
                if args.gpu is not None and torch.cuda.is_available():
                    images = images.cuda(args.gpu, non_blocking=True)  # 移动到相应设备
                if torch.backends.mps.is_available():
                    images = images.to('mps')
                    target = target.to('mps')
                if torch.cuda.is_available():
                    target = target.cuda(args.gpu, non_blocking=True)

                # compute output
                output = model(images)
                loss = criterion(output, target)

                # measure accuracy and record loss
                acc1, acc5 = accuracy(output, target, topk=(1, 5))
                losses.update(loss.item(), images.size(0))
                top1.update(acc1[0], images.size(0))
                top5.update(acc5[0], images.size(0))

                running_loss += loss.item()
                running_accu += acc5[0]
                # measure elapsed time
                batch_time.update(time.time() - end)
                end = time.time()

                if i % args.print_freq == 0:
                    progress.display(i + 1)

                predicted_labels = torch.argmax(output, dim=1)
                misclassified_indices = predicted_labels != target
                for j in range(len(images)):
                    if misclassified_indices[j]:
                        wrong_file.append(loader.dataset.samples[i * args.batch_size + j][0])

            writer.add_scalar('validation loss',
                              running_loss / 40,
                              epoch)
            writer.add_scalar('validation accu',
                              running_accu / 40,
                              epoch)
            writer.flush()

            with open("wrong.txt", 'w') as file:
                for item in wrong_file:
                    file.write(str(item) + '\n')

    batch_time = AverageMeter('Time', ':6.3f', Summary.NONE)
    losses = AverageMeter('Loss', ':.4e', Summary.NONE)
    top1 = AverageMeter('Acc@1', ':6.2f', Summary.AVERAGE)
    top5 = AverageMeter('Acc@5', ':6.2f', Summary.AVERAGE)
    progress = ProgressMeter(  # 进度条
        len(val_loader) + (args.distributed and (len(val_loader.sampler) * args.world_size < len(val_loader.dataset))),
        [batch_time, losses, top1, top5],
        prefix='Test: ')

    # switch to evaluate mode
    model.eval()

    run_validate(val_loader)
    if args.distributed:  # 将各个进程的数据进行归约并进行聚合，以得到全局的准确率。
        top1.all_reduce()
        top5.all_reduce()

    if args.distributed and (len(val_loader.sampler) * args.world_size < len(val_loader.dataset)):  # 验证集数据不足的情况
        aux_val_dataset = Subset(val_loader.dataset,
                                 range(len(val_loader.sampler) * args.world_size, len(val_loader.dataset)))
        aux_val_loader = torch.utils.data.DataLoader(
            aux_val_dataset, batch_size=args.batch_size, shuffle=False,
            num_workers=args.workers, pin_memory=True)
        run_validate(aux_val_loader, len(val_loader))

    progress.display_summary()  # 打印

    return top1.avg


def save_checkpoint(state, is_best, filename='checkpoint.pth.tar'):
    torch.save(state, filename)
    if is_best:
        shutil.copyfile(filename, 'model_best.pth.tar')


class Summary(Enum):
    NONE = 0
    AVERAGE = 1
    SUM = 2
    COUNT = 3


class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self, name, fmt=':f', summary_type=Summary.AVERAGE):
        self.name = name
        self.fmt = fmt
        self.summary_type = summary_type
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count

    def all_reduce(self):
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
        total = torch.tensor([self.sum, self.count], dtype=torch.float32, device=device)
        dist.all_reduce(total, dist.ReduceOp.SUM, async_op=False)
        self.sum, self.count = total.tolist()
        self.avg = self.sum / self.count

    def __str__(self):
        fmtstr = '{name} {val' + self.fmt + '} ({avg' + self.fmt + '})'
        return fmtstr.format(**self.__dict__)

    def summary(self):
        fmtstr = ''
        if self.summary_type is Summary.NONE:
            fmtstr = ''
        elif self.summary_type is Summary.AVERAGE:
            fmtstr = '{name} {avg:.3f}'
        elif self.summary_type is Summary.SUM:
            fmtstr = '{name} {sum:.3f}'
        elif self.summary_type is Summary.COUNT:
            fmtstr = '{name} {count:.3f}'
        else:
            raise ValueError('invalid summary type %r' % self.summary_type)

        return fmtstr.format(**self.__dict__)


class ProgressMeter(object):
    def __init__(self, num_batches, meters, prefix=""):
        self.batch_fmtstr = self._get_batch_fmtstr(num_batches)
        self.meters = meters
        self.prefix = prefix

    def display(self, batch):
        entries = [self.prefix + self.batch_fmtstr.format(batch)]
        entries += [str(meter) for meter in self.meters]
        print('\t'.join(entries))

    def display_summary(self):
        entries = [" *"]
        entries += [meter.summary() for meter in self.meters]
        print(' '.join(entries))

    def _get_batch_fmtstr(self, num_batches):
        num_digits = len(str(num_batches // 1))
        fmt = '{:' + str(num_digits) + 'd}'
        return '[' + fmt + '/' + fmt.format(num_batches) + ']'


def accuracy(output, target, topk=(1,)):
    """Computes the accuracy over the k top predictions for the specified values of k"""
    with torch.no_grad():
        maxk = max(topk)
        batch_size = target.size(0)

        _, pred = output.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(target.view(1, -1).expand_as(pred))

        res = []
        for k in topk:
            correct_k = correct[:k].reshape(-1).float().sum(0, keepdim=True)
            res.append(correct_k.mul_(100.0 / batch_size))
        return res


if __name__ == '__main__':
    main()