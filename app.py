from apify_client import ApifyClient

import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_upstage import ChatUpstage

import os
import json


solarllm = ChatUpstage()
apify_client = ApifyClient(os.getenv("APIFY_TOKEN"))

MAX_CONTEXT_LENGTH = 30000


def get_facebook_posts(facebook_url: str, n: int = 20):

    # Prepare the Actor input
    run_input = {
        "startUrls": [{"url": facebook_url}],
        "resultsLimit": n,
    }

    # Run the Actor and wait for it to finish
    run = apify_client.actor("apify/facebook-posts-scraper").call(run_input=run_input)

    # Fetch and print Actor results from the run's dataset (if there are any)
    print(
        "💾 Check your data here: https://console.apify.com/storage/datasets/"
        + run["defaultDatasetId"]
    )

    previous_posts = []
    for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
        print(
            item.get("text"),
            item.get("likes"),
            item.get("comments"),
            item.get("shares"),
        )
        previous_posts.append(
            {
                "text": item.get("text"),
                "likes": item.get("likes"),
                "comments": item.get("comments"),
                "shares": item.get("shares"),
            }
        )

    return previous_posts


def get_subject(posts_text: str):

    prompt = ChatPromptTemplate.from_template(
        """You are a good writer.
Plase generate a new and interesting subject based on my previous facebook posts.
It should be interesting and engaging. 
You can consider thr likes, comments, and shares of the previous posts.

Provide a short subject. The output should be a single line and only include the subject.
---
PREVIOUS POSTS:
{posts}
---
Suggested Subject:
"""
    )

    chain = prompt | solarllm | StrOutputParser()
    response = chain.invoke({"posts": posts_text})
    return response


def get_new_posts(subject, previous_posts_text):
    prompt = ChatPromptTemplate.from_template(
        """You are a good writer.
Plase generate a new and interesting facebook post based on the subject and my previous facebook posts. 
Please learn tones and styles from the previous posts
Generate a new post that is interesting and engaging as written by the same author.

Write in the language of the previous posts and the subject. 
For example, if the subject is in English, write in English. 
If the subject is in Korean, write in Korean.
---
PREVIOUS POSTS:
{posts}
---
Suggested Subject: {subject}
---
New Post:
"""
    )

    chain = prompt | solarllm | StrOutputParser()

    response = chain.invoke({"posts": previous_posts_text, "subject": subject})
    return response


# Global state
if "facebook_posts" not in st.session_state:
    st.session_state.facebook_posts = []

if "suggested_subject" not in st.session_state:
    st.session_state.suggested_subject = ""

if "new_post" not in st.session_state:
    st.session_state.new_post = ""

if __name__ == "__main__":
    st.set_page_config(
        page_title="Solar Writer ✍",
        page_icon="✍",
        layout="wide",
    )
    st.title("Solar Writer ✍")
    st.write(
        """This app generates new facebook posts based on your previous facebook posts.
Only three steps are needed:
1. Enter your facebook URL.
2. Press "Generate Post Subject" to generate a new post subject. Or Enter your own subject.
3. Press "Generate New Post" to generate a new post based on the subject and previous posts.
"""
    )

    with st.form("facebook_form"):
        facebook_url = st.text_input(
            "Enter your facebook URL:", "https://www.facebook.com/hunkims"
        )

        submitted = st.form_submit_button("Get Facebook Posts")
        if submitted:
            with st.status("Getting Facebook Posts from {}".format(facebook_url)):
                st.session_state.facebook_posts = get_facebook_posts(facebook_url)
                st.write(st.session_state.facebook_posts)
        elif st.session_state.facebook_posts:
            with st.expander(
                "Previous Facebook Posts ({})".format(
                    len(st.session_state.facebook_posts)
                )
            ):
                st.write(st.session_state.facebook_posts)

    if st.session_state.facebook_posts:
        # Get the text of the previous posts up to the maximum context length
        posts_text = ""
        for post in st.session_state.facebook_posts:
            post_dump = json.dumps(post)
            if len(posts_text) + len(post_dump) > MAX_CONTEXT_LENGTH:
                break
            posts_text += post["text"] + "\n"

            print(posts_text)

        with st.form("generate_subject_form"):
            generate_subject_buttom_title = "Generate Post Subject"
            if st.session_state.suggested_subject:
                generate_subject_buttom_title = "Regenerate Post Subject"

            if st.form_submit_button(generate_subject_buttom_title):
                with st.spinner("Generating Post Subject ..."):
                    st.session_state.new_post = ""
                    st.session_state.suggested_subject = get_subject(posts_text)

            st.session_state.suggested_subject = st.text_input(
                "Proposed Subject:", st.session_state.suggested_subject
            )

        if st.session_state.suggested_subject:
            with st.form("generate_new_post_form"):
                if st.form_submit_button("Generate New Post"):
                    with st.spinner("Generating New Post ..."):
                        st.session_state.new_post = get_new_posts(
                            st.session_state.suggested_subject, posts_text
                        )

                if st.session_state.new_post:
                    st.session_state.new_post = st.text_area(
                        "New Post:",
                        st.session_state.new_post,
                        height=200 + len(st.session_state.new_post) // 5,
                    )

            if st.session_state.new_post:
                # Add download button
                st.download_button(
                    label="Download New Post",
                    data=st.session_state.new_post,
                    file_name="new_post.txt",
                    mime="text/plain",
                )
