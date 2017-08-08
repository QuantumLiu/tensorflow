# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""A Python interface for creating TensorFlow servers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import tensorflow as tf
from tensorflow.core.framework import device_attributes_pb2
from tensorflow.python import pywrap_tensorflow


def list_local_devices():
  """List the available devices available in the local process.

  Returns:
    A list of `DeviceAttribute` protocol buffers.
  """
  def _convert(pb_str):
    m = device_attributes_pb2.DeviceAttributes()
    m.ParseFromString(pb_str)
    return m

  return [_convert(s) for s in pywrap_tensorflow.list_devices()]


def check_gpus():
    '''
    GPU available check
    reference : http://feisky.xyz/machine-learning/tensorflow/gpu_list.html
    '''
    all_gpus = [x.name for x in list_local_devices() if x.device_type == 'GPU']
    if not all_gpus:
        print('This script could only be used to manage NVIDIA GPUs,but no GPU found in your device')
        return False
    elif not 'NVIDIA System Management' in os.popen('nvidia-smi -h').read():
        print("'nvidia-smi' tool not found.")
        return False
    return True

if check_gpus():
    def parse(line,qargs):
        '''
        line:
            a line of text
        qargs:
            query arguments
        return:
            a dict of gpu infos
        Pasing a line of csv format text returned by nvidia-smi
        解析一行nvidia-smi返回的csv格式文本
        '''
        numberic_args = ['memory.free', 'memory.total', 'power.draw', 'power.limit']#可计数的参数
        power_manage_enable=lambda v:(not 'Not Support' in v)#lambda表达式，显卡是否滋瓷power management（笔记本可能不滋瓷）
        to_numberic=lambda v:float(v.upper().strip().replace('MIB','').replace('W',''))#带单位字符串去掉单位
        process = lambda k,v:((int(to_numberic(v)) if power_manage_enable(v) else 1) if k in numberic_args else v.strip())
        return {k:process(k,v) for k,v in zip(qargs,line.strip().split(','))}
    
    def query_gpu(qargs=[]):
        '''
        qargs:
            query arguments
        return:
            a list of dict
        Querying GPUs infos
        查询GPU信息
        '''
        qargs =['index','gpu_name', 'memory.free', 'memory.total', 'power.draw', 'power.limit']+ qargs
        cmd = 'nvidia-smi --query-gpu={} --format=csv,noheader'.format(','.join(qargs))
        results = os.popen(cmd).readlines()
        return [parse(line,qargs) for line in results]
    
    def power(d):
        '''
        helper function fo sorting gpus by power
        '''
        power_infos=(d['power.draw'],d['power.limit'])
        if any(v==1 for v in power_infos):
            print('Power management unable for GPU {}'.format(d['index']))
            return 1
        return float(d['power.draw'])/d['power.limit']
    
    class GPUManager():
        '''
        qargs:
            query arguments
        A manager which can list all available GPU devices
        and sort them and choice the most free one.
        GPU设备管理器，考虑列举出所有可用GPU设备，并加以排序，自动选出
        最空闲的设备。
        '''
        def __init__(self,qargs=[]):
            '''
            '''
            self.qargs=qargs
            self.gpus=query_gpu(qargs)
            self.gpu_num=len(self.gpus)
    
        def sort_by_memory(self,by_size=False,qargs=[]):
            self.gpus=query_gpu(self.qargs+qargs)
            if by_size:
                print('Sorted by free memory size')
                return sorted(self.gpus,key=lambda d:d['memory.free'],reverse=True)
            else:
                print('Sorted by free memory rate')
                return sorted(self.gpus,key=lambda d:float(d['memory.free'])/ d['memory.total'],reverse=True)
    
        def sort_by_power(self,qargs=[]):
            self.gpus=query_gpu(self.qargs+qargs)
            return sorted(self.gpus,key=power)
        
        def sort_by_cust(self,key,qargs=[],reverse=False):
            qargs=self.qargs+qargs
            self.gpus=query_gpu(qargs)
            if isinstance(key,str) and (key in qargs):
                return sorted(self.gpus,key=lambda d:d[key],reverse=reverse)
            if isinstance(key,type(lambda a:a)):
                return sorted(self.gpus,key=key,reverse=reverse)
            raise ValueError("The argument 'key' must be a function or a key in query args")

        def auto_choice(self,mode=0):
            '''
            mode:
                0:(default)sorted by free memory size
            return:
                a TF device object
            Auto choice the freest GPU device
            自动选择最空闲GPU
            Example:
            gm=GPUManager()
            with gm.auto_choice():
                blabla
            '''
            if mode==0:
                print('Choosing the GPU device has largest free memory...')
                chosen_gpu=self.sort_by_memory(True)[0]
            elif mode==1:
                print('Choosing the GPU device has highest free memory rate...')
                chosen_gpu=self.sort_by_power()[0]
            elif mode==2:
                print('Choosing the GPU device by power...')
                chosen_gpu=self.sort_by_power()[0]
            else:
                print('Given an unaviliable mode,will be chosen by memory')
                chosen_gpu=self.sort_by_memory()[0]
            index=chosen_gpu['index']
            print('Using GPU {i}:\n{info}'.format(i=index,info='\n'.join([str(k)+':'+str(v) for k,v in chosen_gpu.items()])))
            return tf.device('/gpu:{}'.format(index))
else:
    def parse(line,qargs):
        raise ImportError('GPU available check failed')
    def query_gpu(qargs=[]):
        raise ImportError('GPU available check failed')    
    class GPUManager():
        raise ImportError('GPU available check failed')
        def __init__(self,qargs=[]):
            raise ImportError('GPU available check failed')
        def sort_by_memory(self,by_size=False,qargs=[]):
            raise ImportError('GPU available check failed')
    
        def sort_by_power(self,qargs=[]):
            raise ImportError('GPU available check failed')
        
        def sort_by_cust(self,key,qargs=[],reverse=False):
            raise ImportError('GPU available check failed')

        def auto_choice(self,mode=0):
            raise ImportError('GPU available check failed')
