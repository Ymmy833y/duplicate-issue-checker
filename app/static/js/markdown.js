import { marked } from 'marked';

const convertMarkdownToHtml = (markdownText) => {
    return marked(markdownText);
}

window.convertMarkdownToHtml = convertMarkdownToHtml;
