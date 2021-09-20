import json
import os
import re
import csv
import warnings
import sys

warnings.simplefilter("ignore", DeprecationWarning)# Load the LDA model from sk-learn

from sklearn.metrics.pairwise import cosine_similarity


from spacy.lang.en import English
parser = English()

import collections


import nltk
nltk.download('wordnet')
from nltk.corpus import wordnet as wn
from nltk.stem.wordnet import WordNetLemmatizer
nltk.download('stopwords')

import matplotlib.pyplot as plt

from gensim import corpora
import pickle
import gensim
import pyLDAvis.gensim

def tokenize(text):
    lda_tokens = []
    tokens = parser(text)
    for token in tokens:
        if token.orth_.isspace():
            continue
        elif token.like_url:
            lda_tokens.append('URL')
        elif token.orth_.startswith('@'):
            lda_tokens.append('SCREEN_NAME')
        else:
            lda_tokens.append(token.lower_)
    return lda_tokens



def get_lemma(word):
    lemma = wn.morphy(word)
    if lemma is None:
        return word
    else:
        return lemma

def get_lemma2(word):
    return WordNetLemmatizer().lemmatize(word)


def prepare_text_for_lda(tokens1):
    en_stop = set(nltk.corpus.stopwords.words('english'))
    #tokens = tokenize(text)
    tokens = [token for token in tokens1 if len(token) > 1]
    tokens = [token for token in tokens if token not in en_stop]
    tokens = [get_lemma(token) for token in tokens]
    return tokens



def count_words(words , dict):
    c = collections.Counter(words)
    for w in c:
        if w in dict.keys():
            dict[w]['count files'] += 1
            dict[w]['count total'] += c[w]
        else:
            dict[w] = {
                'count files': 1,
                'count total': c[w]
            }

def remove_number(list):
    new_list = []
    for word in list:
        if word != '':
            try:
                tmp = int(word)
            except:
                new_list.append(word)

    return new_list

def find_average_commit_length (all_commits_for_func, func_to_avg, func_name):
    avg = 0
    for commit in all_commits_for_func:
        seperated = commit.split(sep= ' ')
        avg += (len(seperated) / len(all_commits_for_func))
    func_to_avg[func_name] = avg


def remove_low_appearence_words(strings, counts):
    words_to_remove = []
    for word in counts:
        if int(counts[word]['count total']) < 6:
            words_to_remove.append(word)
    for dict in strings:
        list = dict['messages']
        tmp = []
        for word in list:
            if word not in words_to_remove:
                tmp.append(word)
        dict['messages']= tmp
    return strings

def clean_list_of_strings(old):
    try:
        filtered = list(map(lambda x: re.sub("[./`]", '\n', x), old))
        filtered = list(map(lambda x: re.sub("[!-,]", '\n', x), filtered))
        filtered = list(map(lambda x: re.sub("[:-@]", '\n', x), filtered))
        filtered = list(map(lambda x: re.sub("[\[-^]", '\n', x), filtered))
        filtered = list(map(lambda x: re.sub("[{-~]", '\n', x), filtered))

        filtered = list(map(lambda x: re.sub('\n+', ' ', x),filtered))
        filtered = list(map(lambda x: re.sub('\r+', ' ', x),filtered))

        filtered = list(map(lambda x: re.sub(' +', ' ', x),filtered))
        filtered = list(map(lambda x: re.sub(' +', ' ', x),filtered))

        filtered = list(map(lambda x: x.lower(),filtered))
        filtered = list(map(lambda x: x.split(sep="git-svn")[0],filtered))

        return filtered
    except:
        return []


class TopicModeling:

    def __init__(self, project_name):
        self.project_path = os.path.join(os.getcwd(), "projects", project_name)
        self.topicModeling_path = os.path.join(self.project_path, "topicModeling")
        self.analysis_path = os.path.join(self.project_path, "analysis")

    def run(self):

        if not (os.path.exists(os.path.join(self.analysis_path, "func to commits message.txt"))):
            print("missing data")

        else:
            if not (os.path.exists(self.topicModeling_path)):
                os.mkdir(self.topicModeling_path)

            if not (os.path.exists(os.path.join(self.topicModeling_path,"bug to funcion and similarity"))):
                os.mkdir(os.path.join(self.topicModeling_path,"bug to funcion and similarity"))

            if not (os.path.exists(os.path.join(self.topicModeling_path,"topics"))):
                os.mkdir(os.path.join(self.topicModeling_path,"topics"))

            if not (os.path.exists(os.path.join(self.topicModeling_path,"filtered_data.txt"))):
                with open(os.path.join(self.analysis_path, "func to commits message.txt")) as outfile:
                    data = json.load(outfile)

                data = data['functions']
                all_func_to_commit_messages = []
                func_to_avg = {}
                word_to_counts = {} # word to how many times it showed up and in how many files

        # data cleaning
                for func_name in data.keys():
                    # returns a list, each element in the list is a filtered commit message
                    filtered = clean_list_of_strings(data[func_name]['message'])

                    find_average_commit_length(filtered, func_to_avg,func_name)
                    func_to_commit_messages = {
                        'func_name': func_name,
                        'commit_messages':  ' '.join(str(e) for e in filtered)}

                    # list of dictionaries each represent func and one string of all commit messages
                    all_func_to_commit_messages.append(func_to_commit_messages)


                func_to_prepared_commit_messages = []
                for func in all_func_to_commit_messages:
                    messages = func['commit_messages']
                    list_of_words = messages.split(sep=" ")
                    list_of_words_without_numbers = remove_number(list_of_words)

                    # prepared text for lda, removed stop words and small words
                    text_data = prepare_text_for_lda(list_of_words_without_numbers)

                    count_words(text_data, word_to_counts)
                    func_to_prepared_commit_messages.append({
                        'func_name': func['func_name'],
                        'messages': text_data})

                func_to_prepared_commit_messages = remove_low_appearence_words(func_to_prepared_commit_messages, word_to_counts)

                self.save_into_file("word_to_counts", word_to_counts, 'words')
                self.save_into_file("filtered_data" , func_to_prepared_commit_messages, 'strings')
                self.save_into_file("function_to_avg_commit_len", func_to_avg, 'function to avg')
            else:
                with open(os.path.join(self.topicModeling_path,"filtered_data.txt")) as outfile:
                    func_to_prepared_commit_messages = json.load(outfile)['strings']
                with open(os.path.join(self.topicModeling_path,"word_to_counts.txt")) as outfile:
                    word_to_counts = json.load(outfile)['words']

            # gather the prepared messages
            prepared_commit_messages = list(dict['messages'] for dict in func_to_prepared_commit_messages)

            dictionary = corpora.Dictionary(prepared_commit_messages)
            corpus = [dictionary.doc2bow(text) for text in prepared_commit_messages]
            pickle.dump(corpus, open(os.path.join(self.topicModeling_path,"corpus.pkl"), 'wb'))
            dictionary.save(os.path.join(self.topicModeling_path,"dictionary.gensim"))



            num_topics_to_table = [
                ['num of topics' ,
                 'bug id',
                 'num of functions that changed' ,
                 'num of functions that changed no tests' ,
                 'max index all functions',
                 'num of functions checked',
                 'max index all functions no test functions',
                 'num of functions checked',
                 'max index exist functions',
                 'num of functions checked',
                 'max index exist functions no tests',
                 'num of functions checked']]

            for NUM_TOPICS in range(15,26):
                ldamodel = gensim.models.ldamodel.LdaModel(corpus, num_topics = NUM_TOPICS, id2word=dictionary, passes=15)
                # returns the table of bug to max index for NUM TOPICS
                num_topics_to_table.extend(
                    self.bug_to_func_and_similarity(ldamodel, dictionary, func_to_prepared_commit_messages, NUM_TOPICS))
                ldamodel.save(self.project_path +'\\topicModeling\\topics\\model'+ str(NUM_TOPICS)+'.gensim')

                #topics = ldamodel.print_topics(num_words=4)
                #for topic in topics:
                #    print(topic)
                print("finished %d topics" %(NUM_TOPICS))

            # after the data of each num_topics is gathered, create the csv table
            self.create_table(num_topics_to_table)




    def bug_to_func_and_similarity(self,  lda,dictionary,prepared_commit_messages, NUM_TOPICS):
        with open(self.project_path + "\\analysis\\bug_to_commit_that_solved.txt") as outfile:
            bugs = json.load(outfile)['bugs to commit']

        if not (os.path.exists(self.project_path + "\\topicModeling\\bug to funcion and similarity\\bug to functions and similarity " + str(NUM_TOPICS) + " topics.txt")):
            all_bugs = []  # del

            bugs_filtered_and_document_topics = []
            for bug in bugs:
                chances = []
                description = clean_list_of_strings([bug['description']])
                if description != []:
                    description=description[0].split(sep=' ')
                all_bugs.extend(description)

                # topic number to the chance for the bug being in th topic
                topic_to_chances = lda.get_document_topics(bow = dictionary.doc2bow(description), minimum_probability=0)
                for tup in topic_to_chances:
                    chances.append(tup[1])
                bugs_filtered_and_document_topics.append({
                    'bug id': bug['bug id'],
                    'chances': chances
                })

            func_filtered_and_document_topics = []
            for func in prepared_commit_messages:
                chances = []
                bow = dictionary.doc2bow(func['messages'])
                topic_to_chances = lda.get_document_topics(bow = bow, minimum_probability=0)
                for tup in topic_to_chances:
                    chances.append(tup[1])
                func_filtered_and_document_topics.append({
                    'func name': func['func_name'],
                    'chances': chances
                })



            i = len(bugs_filtered_and_document_topics)
            bug_to_func_and_similarity={}

            for bug in bugs_filtered_and_document_topics:
                func_and_similarity =[]
                for func in func_filtered_and_document_topics:
                    cos = cosine_similarity([bug['chances']],[func['chances']]).tolist()[0][0]
                    func_and_similarity.append((func['func name'],cos))

                func_and_similarity.sort(key=lambda x: x[1] , reverse=True)
                func_and_similarity_with_index = []
                index = 0
                for f_and_s in func_and_similarity:
                    func_and_similarity_with_index.append((f_and_s[0],f_and_s[1],index))
                    index += 1
                bug_to_func_and_similarity[bug['bug id']] = func_and_similarity_with_index
                print(i)
                i-=1

            print("finished " + str(NUM_TOPICS) + " topics")
            self.save_into_file("bug to funcion and similarity\\bug to functions and similarity " + str(NUM_TOPICS) + " topics" ,bug_to_func_and_similarity,'bugs')


        with open(self.project_path + "\\topicModeling\\bug to funcion and similarity\\bug to functions and similarity " + str(NUM_TOPICS) + " topics.txt") as outfile:
            bug_to_func_and_similarity = json.load(outfile)['bugs']
        with open(self.project_path + "\\analysis\\commitId to all functions.txt") as outfile:
            commit_to_exist_functions = json.load(outfile)['commit id']

        return self.fill_table(NUM_TOPICS,bugs,bug_to_func_and_similarity, commit_to_exist_functions)



    def fill_table(self, NUM_TOPICS, bugs , bug_to_func_and_similarity, commit_to_exist_functions):
        ret_list = []  # will hold tuples that each one represent bug id, num of funcs that changed, max index of changed func

        i= 1
        for bug in bugs:
            if len(bug['function that changed']) > 10:
                continue

            index_len_all_funcs = self.find_max_index_all_functions(bug,bug_to_func_and_similarity)
            index_len_all_funcs_no_tests = self.find_max_index_all_functions_no_tests(bug,bug_to_func_and_similarity)
            index_len_exist_funcs = self.find_max_index_exist_functions(bug,bug_to_func_and_similarity, commit_to_exist_functions[str(bug['commit number'])]['all functions'])
            index_len_exist_funcs_no_tests = self.find_max_index_exist_functions_no_tests(bug,bug_to_func_and_similarity, commit_to_exist_functions[str(bug['commit number'])]['all functions'])

            ret_list.append([NUM_TOPICS, # how many topics we are using
                        bug['bug id'],  # issue id
                        len(bug['function that changed']),  # num of functions that changed in the commit
                         # num of functions that changed in the commit without tests
                        len(list(func for func in bug['function that changed'] if ("test" or "Test") not in func['function name'])),
                        str(index_len_all_funcs[0]),
                        str(index_len_all_funcs[1]),
                        str(index_len_all_funcs_no_tests[0]),
                        str(index_len_all_funcs_no_tests[1]),
                        str(index_len_exist_funcs[0]),
                        str(index_len_exist_funcs[1]),
                        str(index_len_exist_funcs_no_tests[0]),
                        str(index_len_exist_funcs_no_tests[1])
                        ])


            print("finished bug number " + str(i))
            i += 1

        return ret_list


    def find_max_index_all_functions(self, bug,bug_to_func_and_similarity):
        max_index = -1
        func_and_similarity_of_bug = bug_to_func_and_similarity[bug['bug id']]
        for func in bug['function that changed']:
            for func_and_similarity in func_and_similarity_of_bug:
                if func['function name'] == func_and_similarity[0]:
                    max_index = max(max_index,func_and_similarity[2])
                    break

        return max_index, len(func_and_similarity_of_bug)


    def find_max_index_all_functions_no_tests(self, bug,bug_to_func_and_similarity):
        max_index_without_test = -1
        func_and_similarity_of_bug = bug_to_func_and_similarity[bug['bug id']]

    # filtering all the test functions
        func_and_similarity_of_bug_without_tests = list(func for func in func_and_similarity_of_bug if ("test" or "Test") not in func[0])
        functions_that_changed_no_tests = list(func for func in bug['function that changed'] if ("test" or "Test") not in func['function name'])

        if len(functions_that_changed_no_tests) == 0:
            return -1, len(func_and_similarity_of_bug_without_tests)

        for func in functions_that_changed_no_tests:
            index = 0
            for func_and_similarity_no_test in func_and_similarity_of_bug_without_tests:
                if func['function name'] == func_and_similarity_no_test[0]:
                    max_index_without_test = max(max_index_without_test,index)
                    break
                index += 1

        return max_index_without_test, len(func_and_similarity_of_bug_without_tests)


    def find_max_index_exist_functions(self, bug,bug_to_func_and_similarity ,exists_functions):
        max_index_smaller_list = -1

        func_and_similarity_of_bug = bug_to_func_and_similarity[bug['bug id']].copy()
    # now im finiding the index only on the list of existing functions in the commit
        exist_funcs_with_similarity = []

        for func_exist in exists_functions:
            for func_and_similarity in func_and_similarity_of_bug:
                if func_exist == func_and_similarity[0]:
                    exist_funcs_with_similarity.append(func_and_similarity)
                    func_and_similarity_of_bug.remove(func_and_similarity)
                    break
        exist_funcs_with_similarity.sort(key=lambda x: x[1], reverse=True)

        for func in bug['function that changed']:
            index = 0
            for exist_func_and_similarity in exist_funcs_with_similarity:
                if func['function name'] == exist_func_and_similarity[0]:
                    max_index_smaller_list = max(max_index_smaller_list, index)
                    break
                index += 1

        return max_index_smaller_list, len(exist_funcs_with_similarity)


    def find_max_index_exist_functions_no_tests(self, bug,bug_to_func_and_similarity ,exists_functions):
        max_index_smaller_list_no_tests = -1

        func_and_similarity_of_bug = bug_to_func_and_similarity[bug['bug id']].copy()
    # now im finiding the index only on the list of existing functions in the commit
        exist_funcs_with_similarity = []

        for func_exist in exists_functions:
            for func_and_similarity in func_and_similarity_of_bug:
                if func_exist == func_and_similarity[0]:
                    exist_funcs_with_similarity.append(func_and_similarity)
                    func_and_similarity_of_bug.remove(func_and_similarity)
                    break
        exist_funcs_with_similarity.sort(key=lambda x: x[1] , reverse=True)


        exist_funcs_with_similarity_without_tests = list(func for func in exist_funcs_with_similarity if ("test" or "Test") not in func[0])
        functions_that_changed_no_tests = list(func for func in bug['function that changed'] if ("test" or "Test") not in func['function name'])

        if len(functions_that_changed_no_tests) == 0:
            return -1, len(exist_funcs_with_similarity_without_tests)

        for func in functions_that_changed_no_tests:
            index = 0
            for exist_func_and_similarity in exist_funcs_with_similarity_without_tests:
                if func['function name'] == exist_func_and_similarity[0]:
                    max_index_smaller_list_no_tests = max(max_index_smaller_list_no_tests,index)
                    break
                index += 1

        return max_index_smaller_list_no_tests, len(exist_funcs_with_similarity_without_tests)





    def create_table(self, rows):
        with open(self.project_path +'\\topicModeling\\table.csv', 'w', newline='', ) as file:
            writer = csv.writer(file)
            writer.writerows(rows)



    def save_into_file(self, file_name, new_data, dictionary_value):
        data = {}
        data[dictionary_value] = new_data
        with open(self.project_path + "\\topicModeling\\" + file_name + ".txt", 'w') as outfile:
            json.dump(data, outfile, indent=4)


    def visualize(self, NUM_TOPICS):

        dictionary = gensim.corpora.Dictionary.load(self.project_path +'\\topicModeling\\dictionary.gensim')
        corpus = pickle.load(open(self.project_path +'\\topicModeling\\corpus.pkl', 'rb'))
        lda = gensim.models.ldamodel.LdaModel.load(self.project_path +'\\topicModeling\\topics\\model'+ str(NUM_TOPICS)+'.gensim')
        lda_display = pyLDAvis.gensim.prepare(lda, corpus, dictionary, sort_topics=False)
        pyLDAvis.display(lda_display)

if __name__ == "__main__":
    project_name ="apache_commons-lang"
    if len(sys.argv) == 2:
        project_name = str(sys.argv[1])
    TopicModeling(project_name).run()
