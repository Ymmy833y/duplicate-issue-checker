document.querySelector('#search-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());

    const response = await fetch('/search', {
        method: 'POST',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });

    if (response.ok) {
        const result = await response.json();
        updateErrorMessage();
        updateRelatedIssues(result);
    } else {
        const errorData = await response.json();
        console.error(`Error: ${errorData.errorMessage || "Unable to fetch data."}`);
        document.querySelector('#related-issues-content').classList.add('hidden');
        updateErrorMessage(errorData.errorMessage);
    }
});

const updateRelatedIssues = (data) => {
    const { detail, issues } = data;

    updateDetailContent(detail);
    updateIssuesContent(issues);
    document.querySelector('#related-issues-content').classList.remove('hidden');
    document.querySelector('#issuesHeader').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

const updateDetailContent = (detail) => {
    const { total, message } = detail;

    const color = (total == 0) ? 'green' : 'yellow';
    const icon = (total == 0)
        ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />'
        : `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
            d="M9 12h6m-6 4h6m-3-8h.01M7 20h10a2 2 0 002-2V6a2 2 0 00-2-2H7a2 2 0 00-2 2v12a2 2 0 002 2z" />`;

    document.querySelector('#detail-content').outerHTML = `
        <div id="detail-content" 
            class="flex items-center bg-${color}-100 border-l-4 border-${color}-500 text-${color}-700 p-4 rounded mb-4">
            <svg class="w-6 h-6 mr-2 text-${color}-500" xmlns="http://www.w3.org/2000/svg" 
                fill="none" viewBox="0 0 24 24" stroke="currentColor">${icon}</svg>
            <p>${message}</p>
        </div>
    `;
}

const updateIssuesContent = (issues) => {
    const issuesContent = document.querySelector('#issues-content');
    issuesContent.innerHTML = '';
    for (const issue of issues) {
        const { number, title, url, state, comments, threshold } = issue;
        const issueContent = document.createElement('li');
        issueContent.classList.add('border', 'border-gray-300', 'rounded', 'p-4');
        issueContent.appendChild(createIssueHeader(number, title, url, state));
        issueContent.appendChild(createThresholdContent(threshold));
        issueContent.appendChild(createCommentContent(comments));

        issuesContent.appendChild(issueContent);
    }
}

const createIssueHeader = (number, title, url, state) => {
    state = String(state).toUpperCase();
    let color = 'gray';
    if (state == 'OPEN') color = 'green';
    else if (state == 'CLOSED') color = 'red';
    else if (state == 'MERGED') color = 'purple';

    const template = document.createElement('template');
    template.innerHTML = `
        <div class="flex justify-between items-center">
            <a href="${url}" target="_blank"
                class="text-lg font-semibold text-blue-600 hover:underline">
                #${number} ${title}
            </a>
            <span class="ml-2 px-3 py-1 rounded-full text-white text-sm bg-${color}-500">
                ${state}
            </span>
        </div>
    `;
    return template.content.firstElementChild;
}

const createThresholdContent = (threshold) => {
    threshold = Number(threshold);

    let color, type, message;
    if (threshold >= 0.8) {
        color = 'green';
        type = 'High similarity';
        message = 'The vectors are very closely aligned.';
    } else if (threshold >= 0.7) {
        color = 'blue';
        type = 'Moderate similarity';
        message = 'The vectors are fairly aligned.';
    } else if (threshold >= 0.5) {
        color = 'yellow';
        type = 'Low similarity';
        message = 'Some degree of similarity is observed.';
    } else {
        color = 'red';
        type = 'Minimal similarity';
        message = 'The vectors are mostly unrelated.';
    }

    const template = document.createElement('template');
    template.innerHTML = `
        <div class="mt-4">
            <p class="text-lg font-semibold">Similarity Threshold</p>
            <div class="mt-2 p-3 flex items-center border rounded-lg shadow-sm bg-${color}-50 border-${color}-400 text-${color}-700">
                <div>
                    <p class="font-semibold">${type}</p>
                    <p class="text-sm">${message}</p>
                </div>
                <span class="ml-auto px-3 py-1 rounded-lg font-semibold bg-${color}-200 text-${color}-800">
                    ${threshold}
                </span>
            </div>
        </div>
    `;

    return template.content.firstElementChild;
}

const createCommentContent = (comments) => {
    const comment = comments ? convertMarkdownToHtml(comments[0]) : 'No description available.';
    const template = document.createElement('template');
    template.innerHTML = `
        <div class="pt-4">
            <p class="text-xl font-semibold">Description (First comment)</p>
            <div class="markdown-body mt-2 pl-2 max-h-60 overflow-y-auto border-l-4 border-gray-300" 
                ${comment}
            </div>
        </div>
    `;

    return template.content.firstElementChild;
}

const updateErrorMessage = (message) => {
    document.querySelector('#error_message').classList.toggle('hidden', !message);
    document.querySelector('#error_message').querySelector('span').innerText = message;
}
