import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, font
import logging
import requests
import re

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class InputMethodApp:
    def __init__(self, master):
        self.master = master
        master.title("智能输入法")

        # 创建设置变量
        self.model_name = tk.StringVar(value="deepseek-ai/DeepSeek-V2.5")
        self.api_endpoint = tk.StringVar(value="https://api.siliconflow.cn/v1/chat/completions")
        self.api_key = tk.StringVar()
        self.input_mode = tk.StringVar(value="双拼")
        self.use_post_processing = tk.BooleanVar(value=True)
        self.trigger_symbol = tk.StringVar(value=".")
        self.font_size = tk.IntVar(value=12)

        # 创建主界面
        self.create_main_interface()

        # 加载设置
        self.load_settings()

        # 用于存储上一次转换的文本
        self.last_converted_text = ""

    def create_main_interface(self):
        # 创建左右分栏
        paned_window = ttk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # 左侧输入框
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)

        self.input_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        self.input_text.bind('<KeyRelease>', self.check_for_conversion)

        # 右侧输出框
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)

        self.output_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, state='disabled')
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 转换按钮
        convert_button = ttk.Button(self.master, text="转换", command=self.convert_text)
        convert_button.pack(pady=10)

        # 设置按钮
        settings_button = ttk.Button(self.master, text="设置", command=self.open_settings)
        settings_button.pack(pady=10)

        # 字体大小调整
        font_frame = ttk.Frame(self.master)
        font_frame.pack(pady=10)
        ttk.Label(font_frame, text="字体大小:").pack(side=tk.LEFT)
        ttk.Spinbox(font_frame, from_=8, to=24, textvariable=self.font_size, command=self.update_font_size, width=5).pack(side=tk.LEFT)

        # 初始化字体
        self.update_font_size()

    def update_font_size(self):
        current_font = font.Font(font=self.input_text['font'])
        new_font = font.Font(family=current_font.actual()['family'], size=self.font_size.get())
        self.input_text.configure(font=new_font)
        self.output_text.configure(font=new_font)

    def check_for_conversion(self, event):
        current_text = self.input_text.get("1.0", tk.END).strip()
        if current_text.endswith(self.trigger_symbol.get()) and current_text != self.last_converted_text:
            self.last_converted_text = current_text
            threading.Thread(target=self.convert_text).start()

    def convert_text(self):
        input_text = self.input_text.get("1.0", tk.END).strip()
        if input_text:
            processed_text = self.process_input(input_text)
            api_result = self.call_api(processed_text)
            
            if api_result:
                api_result = api_result.replace(" ", "")
                
                if self.use_post_processing.get():
                    api_result = self.post_process(api_result)
                
                self.output_text.config(state='normal')
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, api_result)
                self.output_text.config(state='disabled')
            else:
                logging.error("处理文本失败")

    def open_settings(self):
        settings_window = tk.Toplevel(self.master)
        settings_window.title("设置")

        ttk.Label(settings_window, text="模型名称:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(settings_window, textvariable=self.model_name).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(settings_window, text="API 端点:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(settings_window, textvariable=self.api_endpoint).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(settings_window, text="API 密钥:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(settings_window, textvariable=self.api_key, show="*").grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(settings_window, text="输入模式:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        ttk.Combobox(settings_window, textvariable=self.input_mode, values=["双拼", "全拼"]).grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(settings_window, text="使用后处理:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        ttk.Checkbutton(settings_window, variable=self.use_post_processing).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(settings_window, text="触发符号:").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(settings_window, textvariable=self.trigger_symbol).grid(row=5, column=1, padx=5, pady=5)

        ttk.Button(settings_window, text="保存设置", command=lambda: self.save_settings(settings_window)).grid(row=6, column=0, columnspan=2, pady=10)

    def save_settings(self, settings_window):
        settings = {
            "model_name": self.model_name.get(),
            "api_endpoint": self.api_endpoint.get(),
            "api_key": self.api_key.get(),
            "input_mode": self.input_mode.get(),
            "use_post_processing": self.use_post_processing.get(),
            "trigger_symbol": self.trigger_symbol.get(),
            "font_size": self.font_size.get()
        }
        with open("settings.json", "w") as f:
            json.dump(settings, f)
        logging.debug("设置已保存")
        settings_window.destroy()

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
            self.model_name.set(settings.get("model_name", "deepseek-ai/DeepSeek-V2.5"))
            self.api_endpoint.set(settings.get("api_endpoint", "https://api.siliconflow.cn/v1/chat/completions"))
            self.api_key.set(settings.get("api_key", ""))
            self.input_mode.set(settings.get("input_mode", "双拼"))
            self.use_post_processing.set(settings.get("use_post_processing", True))
            self.trigger_symbol.set(settings.get("trigger_symbol", "."))
            self.font_size.set(settings.get("font_size", 12))
            self.update_font_size()
            logging.debug("设置已加载")
        except FileNotFoundError:
            logging.debug("未找到设置文件，使用默认设置")

    def process_input(self, text):
        if self.input_mode.get() == "双拼":
            return double_pinyin_to_pinyin(text)
        else:
            return text  # 全拼模式不需要转换

    def call_api(self, prompt):
        logging.debug(f"调用API: {prompt}")
        headers = {
            "Authorization": f"Bearer {self.api_key.get()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name.get(),
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位精通汉语拼音的专家，对拼音的规则和中文的使用非常了解，非常擅长阅读拼音字母，并将它们转换成符合简体中文的汉字句子。除了拼写出现了不符合拼写规则的错误，否则不要干扰用户的输入意图。你的任务是阅读用户输入的拼音，并且只返回识别到的汉字内容。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "max_tokens": 4096,
            "temperature": 0.1,
            "n": 1
        }
        try:
            response = requests.post(self.api_endpoint.get(), json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                logging.debug(f"API响应: {result}")
                return result['choices'][0]['message']['content']
            else:
                logging.error(f"API调用失败 {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logging.error(f"API调用异常: {str(e)}")
            return None

    def post_process(self, text):
        logging.debug(f"开始后处理: {text}")
        prompt = f"请检查并纠正以下文本中可能存在的错误，保持原意的同时确保语法正确、表达流畅：\n{text}"
        headers = {
            "Authorization": f"Bearer {self.api_key.get()}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name.get(),
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位中文语言专家，擅长纠正文本中的错误并优化表达。请仔细检查给定的文本，纠正任何拼写、语法或表达上的错误，同时保持原文的意思不变。只返回修正后的文本，不要添加任何解释或额外内容。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "max_tokens": 4096,
            "temperature": 0.1,
            "n": 1
        }
        try:
            response = requests.post(self.api_endpoint.get(), json=payload, headers=headers)
            if response.status_code == 200:
                result = response.json()
                logging.debug(f"后处理API响应: {result}")
                return result['choices'][0]['message']['content']
            else:
                logging.error(f"后处理API调用失败 {response.status_code}: {response.text}")
                return text
        except Exception as e:
            logging.error(f"后处理API调用异常: {str(e)}")
            return text

def xiaohe_to_pinyin(xiaohe_input):
    # 声母映射
    shengmu_map = {
        'b': 'b', 'c': 'c', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h',
        'j': 'j', 'k': 'k', 'l': 'l', 'm': 'm', 'n': 'n', 'p': 'p',
        'q': 'q', 'r': 'r', 's': 's', 't': 't', 'w': 'w', 'x': 'x',
        'y': 'y', 'z': 'z', 'v': 'zh', 'i': 'ch', 'u': 'sh'
    }

    # 韵母映射
    yunmu_map = {
        'a': 'a', 'o': 'o', 'e': 'e', 'i': 'i', 'u': 'u', 'v': 'ü',
        'aa': 'a', 'ah': 'ang', 'ai': 'ai', 'an': 'an', 'ao': 'ao',
        'ee': 'e', 'eh': 'eng', 'ei': 'ei', 'en': 'en', 'er': 'er',
        'oo': 'o', 'ou': 'ou',
        'b': 'in', 'c': 'ao', 'd': 'ai', 'f': 'en', 'g': 'eng', 'h': 'ang',
        'j': 'an', 'm': 'ian', 'n': 'iao', 'p': 'ie',
        'q': 'iu', 'r': 'uan', 't': 'ue', 'w': 'ei',
        'y': 'un', 'z': 'ou'
    }

    # 特殊韵母处理
    special_yunmu = {
        't': {'ue': set('nlzcs'), 've': set('ln')},
        's': {'iong': set('jqx'), 'ong': set('cdghklnstzy')},
        'o': {'uo': set('bdghklmnprtz'), 'o': set('bpmf')},
        'k': {'ing': set('bdhjlmnptxy'), 'uai': set('ghkzc')},
        'l': {'iang': set('jlnqx'), 'uang': set('gkhw')},
        'x': {'ia': set('djlnqx'), 'ua': set('gkh')},
    }

    result = []
    i = 0
    while i < len(xiaohe_input):
        # 处理声母
        if xiaohe_input[i] in shengmu_map:
            shengmu = shengmu_map[xiaohe_input[i]]
            i += 1
        else:
            shengmu = ''

        # 处理韵母
        if i < len(xiaohe_input):
            if i + 1 < len(xiaohe_input) and xiaohe_input[i:i+2] in yunmu_map:
                yunmu = yunmu_map[xiaohe_input[i:i+2]]
                i += 2
            else:
                yunmu = yunmu_map.get(xiaohe_input[i], xiaohe_input[i])
                i += 1

            # 处理特殊韵母情况
            if yunmu in special_yunmu:
                possible_yunmus = special_yunmu[yunmu]
                if shengmu:  # 只在有声母的情况下检查
                    for possible_yunmu, specific_shengmu in possible_yunmus.items():
                        if shengmu[0] in specific_shengmu:
                            yunmu = possible_yunmu
                            break
                else:  # 无声母时，选择第一个可能的韵母
                    yunmu = list(possible_yunmus.keys())[0]
        else:
            yunmu = ''

        # 特殊处理
        if not shengmu:
            if yunmu == 'i':
                result.append('yi')
            elif yunmu == 'u':
                result.append('wu')
            elif yunmu == 'v':
                result.append('yu')
            else:
                result.append(yunmu)
        else:
            result.append(shengmu + yunmu)

    return ''.join(result)

def double_pinyin_to_pinyin(double_pinyin_input):
    logging.debug(f"开始双拼转换: {double_pinyin_input}")
    
    # 使用正则表达式分割输入，保留标点符号
    parts = re.findall(r'[a-z]+|[^a-z\s]|\s+', double_pinyin_input, re.IGNORECASE)
    
    result = []
    for part in parts:
        if part.isalpha():
            # 只对字母部分进行转换
            word_result = []
            i = 0
            while i < len(part):
                if i + 1 < len(part):
                    pinyin = xiaohe_to_pinyin(part[i:i+2])
                    word_result.append(pinyin)
                    i += 2
                else:
                    # 处理最后一个单独的字符
                    pinyin = xiaohe_to_pinyin(part[i])
                    word_result.append(pinyin)
                    i += 1
            result.append(''.join(word_result))
        else:
            # 非字母部分（标点符号或空格）直接添加
            result.append(part)
    
    final_result = ''.join(result)
    logging.debug(f"双拼转换结果: {final_result}")
    return final_result

if __name__ == "__main__":
    root = tk.Tk()
    app = InputMethodApp(root)
    root.mainloop()