"""LifeKit: field answers from packed sources, as a Gradio Space."""

import gradio as gr

from lifekit import walks
from lifekit.corpus import guide_corpus, search_pages
from lifekit.packs import manifest_rows, packs_dir
from lifekit.reference import CHAPTER_PAGES, chapter_of_page, page_count, render_page

SESSION_TITLES = {s.title: s.id for s in walks.SESSIONS}


def _result_markdown(session: walks.Session, finding: walks.Finding) -> str:
    source = session.source_by_id(finding.source)
    lines = [f"## {finding.means}", "", f"> {finding.quote}"]
    if source is not None:
        lines.append(f"\n[{source.title}]({source.url}) ({source.licence})")
    if finding.wait is not None:
        minutes = finding.wait // 60
        lines.append(f"\n**Wait {minutes} min.** {finding.wait_label}")
    return "\n".join(lines)


def _walk_step(session_id: str, answers: dict):
    session = walks.session_by_id(session_id)
    question = walks.next_question(session, answers)
    if question is not None:
        return (
            gr.update(value=f"**{question.ask}**", visible=True),
            gr.update(choices=list(question.options), value=None, visible=True),
            gr.update(value=question.because, visible=True),
            gr.update(value="", visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
        )
    finding = walks.finding_for(session, answers)
    image = (
        str(packs_dir() / "walks" / finding.image) if finding.image else None
    )
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(value=_result_markdown(session, finding), visible=True),
        gr.update(value=image, visible=image is not None),
        gr.update(visible=False),
    )


def start_walk(title: str):
    session = walks.session_by_id(SESSION_TITLES[title])
    answers: dict = {}
    return (session.id, answers, gr.update(value=f"*{session.capture}*"),
            *_walk_step(session.id, answers))


def answer_walk(session_id: str, answers: dict, choice: str | None):
    session = walks.session_by_id(session_id)
    question = walks.next_question(session, answers)
    if question is not None and choice:
        answers = {**answers, question.id: choice}
    return (answers, *_walk_step(session_id, answers))


def _encyclopedia_markdown() -> str:
    corpus = guide_corpus()
    lines = [f"# {corpus['reference']['title']}", ""]
    for tile in corpus["tiles"]:
        lines.append(f"- **{tile['title']}** (chapter {tile['chapter']}, Reference tab)")
    for guide in corpus.get("guides", []):
        tile = next(
            (t for t in corpus["tiles"] if t["id"] == guide.get("tileId")), None
        )
        if tile is not None:
            lines.append(f"\n## {tile['title']}")
        if guide.get("intro"):
            lines.append(guide["intro"])
        for group in guide.get("groups", []):
            lines.append(f"\n### {group.get('title', '')}")
            for item in group.get("items", []):
                title = item.get("title") or item.get("id", "")
                text = item.get("text") or item.get("body") or ""
                lines.append(f"- **{title}**" + (f": {text}" if text else ""))
    return "\n".join(lines)


def show_chapter(chapter: int):
    page = CHAPTER_PAGES[chapter]
    return render_page(page), gr.update(value=page)


def show_page(page: int):
    return render_page(page), gr.update(value=chapter_of_page(page))


def run_search(query: str) -> str:
    query = (query or "").strip()
    if not query:
        return "Type a few words from the situation. Results quote the manual."
    results = search_pages(query)
    if not results:
        return "No match in the pack. Try the expert term for it."
    blocks = []
    for page, passage in results:
        chapter = chapter_of_page(page)
        blocks.append(f"> {passage}\n\nFM 21-76, chapter {chapter}, p. {page}")
    return "\n\n---\n\n".join(blocks)


def _credits_markdown() -> str:
    lines = ["Every asset in the pack, with its source and license.", ""]
    for row in manifest_rows():
        lines.append(
            f"- `{row['path']}`: [{row['source_url']}]({row['source_url']}), "
            f"{row['author']}, {row['license']}"
        )
    return "\n".join(lines)


with gr.Blocks(title="LifeKit") as demo:
    gr.Markdown("# LifeKit\nField answers with the source line behind them.")

    with gr.Tab("Walks"):
        session_choice = gr.Radio(
            choices=list(SESSION_TITLES), value=None, label="Walk"
        )
        capture_note = gr.Markdown()
        gr.Markdown(
            "*Clip capture arrives with the model in phase 2. "
            "The interview answers from what you can see.*"
        )
        walk_session = gr.State("")
        walk_answers = gr.State({})
        question_md = gr.Markdown(visible=False)
        option_radio = gr.Radio(choices=[], visible=False, label="Answer")
        because_md = gr.Markdown(visible=False)
        answer_btn = gr.Button("Answer", visible=False)
        result_md = gr.Markdown(visible=False)
        result_image = gr.Image(visible=False, label="Figure", type="filepath")

        walk_outputs = [question_md, option_radio, because_md, result_md, result_image, answer_btn]
        session_choice.change(
            start_walk,
            inputs=[session_choice],
            outputs=[walk_session, walk_answers, capture_note, *walk_outputs],
        )
        answer_btn.click(
            answer_walk,
            inputs=[walk_session, walk_answers, option_radio],
            outputs=[walk_answers, *walk_outputs],
        )

    with gr.Tab("Encyclopedia"):
        gr.Markdown(_encyclopedia_markdown())

    with gr.Tab("Reference"):
        chapter_drop = gr.Dropdown(
            choices=list(CHAPTER_PAGES), value=1, label="Chapter"
        )
        page_slider = gr.Slider(
            minimum=1, maximum=page_count(), step=1, value=CHAPTER_PAGES[1],
            label="Page",
        )
        page_image = gr.Image(label="FM 21-76", type="pil")
        chapter_drop.input(
            show_chapter, inputs=[chapter_drop], outputs=[page_image, page_slider]
        )
        page_slider.release(
            show_page, inputs=[page_slider], outputs=[page_image, chapter_drop]
        )

    with gr.Tab("Quote search"):
        gr.Markdown(
            "Search the manual. Answers quote the page. "
            "Model answers arrive with phase 2."
        )
        query_box = gr.Textbox(label="Looking for", placeholder="water in desert")
        search_btn = gr.Button("Search")
        search_results = gr.Markdown()
        search_btn.click(run_search, inputs=[query_box], outputs=[search_results])
        query_box.submit(run_search, inputs=[query_box], outputs=[search_results])

    with gr.Tab("Credits"):
        gr.Markdown(_credits_markdown())


if __name__ == "__main__":
    demo.launch()
