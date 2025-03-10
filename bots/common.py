import pandas as pd
import importlib
import cfg

from utils.agent import get_choosed_result_n_times_try
from bots.chat import send_message
from utils.log_wrapper import logger

# Import specific data, split by \t
df = pd.read_csv(cfg.data_path, encoding='utf-8', dtype={'a_id':str}, sep='\t')
logger.info(f"# Load data from {cfg.data_path}")

def get_aid(qid,a_text):
    """ Get the aid by qid and r_text """
    df_selected = df[df['q_id'] == int(qid)]
    df_selected = df_selected[df_selected['a'] == a_text]
    aid = df_selected['a_id'].values[0]
    return aid

def next_q(qid,aid):
    """ Get the next question """
    qid = int(qid)
    next_bot_q_id = df[(df['q_id'] == qid) & (df['a_id'] == aid)]['next_q_id'].values[0]
    next_bot_text = df[df['q_id'] == int(next_bot_q_id)]['text'].values[0]
    next_agent = df[df['q_id'] == int(next_bot_q_id)]['agent'].values[0]
    label = df[df['q_id'] == int(next_bot_q_id)]['label'].values[0]
    if_error = df[df['q_id'] == int(next_bot_q_id)]['if_error'].values[0]
    prefix = df[df['q_id'] == int(next_bot_q_id)]['prefix'].values[0]
    prefix_first = df[df['q_id'] == int(next_bot_q_id)]['prefix_first'].values[0]
    return {
        "next_bot_q_id": next_bot_q_id,
        "next_bot_text": next_bot_text,
        "next_agent": next_agent,
        "error_bot_q_id": if_error,
        "next_bot_label": label,
        "prefix": prefix,
        "prefix_first": prefix_first,
        "if_error": if_error
    }

class Bot():
    def __init__(self):
        self.history = []
        self.first_choose_list = df[df['q_id'] == 0]['a'].values
        self.query_times = cfg.query_times
        self.next_bot_q_id = 0
        self.phones = []

    def init_chat(self,human_response,history):
        while True:
            # Get the first question's answer list
            choose_list = df[df['q_id'] == int(self.next_bot_q_id)]['a'].values
            
            # LLM classification
            r_index,r_text = get_choosed_result_n_times_try(
                item_list = choose_list,
                history = history,
                question = "用户的表达的意思是什么？",
                n = self.query_times
            )

            # Get answer type id
            aid = get_aid(self.next_bot_q_id,r_text)
            
            # Get the next question and other information
            result = next_q(0,aid)
            self.next_bot_q_id = result['next_bot_q_id']
            next_bot_text = result['next_bot_text']
            next_agent = result['next_agent']
            error_bot_q_id = result['error_bot_q_id']
            next_bot_label = result['next_bot_label']
            prefix = result['prefix']
            prefix_first = result['prefix_first']
            if_error = result['if_error']


            # If the next_bot_q_id is -1, then break (end of the conversation)
            if self.next_bot_q_id == -1:
                break

            logger.info(f"# next_bot_q_id: {self.next_bot_q_id}, next_bot_text: {next_bot_text}, next_agent: {next_agent}")
            
            if next_bot_label == "ask_phone" and len(self.phones) > 0:
                next_bot_text = f"请问还是查询刚才的{len(self.phones)}个手机号码吗？"

            human_response,history = send_message(next_bot_text,history=history)
            if next_agent:
                _class = importlib.import_module(f"bots.{next_agent}")
                # Agent
                logger.info(f"# Agent: {next_agent}")
                agent = getattr(_class, "Agent")(history=history,phones=self.phones)
                agnet_response = agent.agent_chat(next_bot_text,human_response)
                self.phones = agent.phones
                human_response,history = send_message(agnet_response,history=history)
                self.now_count = 0
                self.next_bot_q_id = 0
        send_message("感谢您的来电，祝您生活愉快~",history=history)
        
