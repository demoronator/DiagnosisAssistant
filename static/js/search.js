let debounceTimer = null // To prevent too many requests
let controller = null // To cancel requests

const onInput = (event) => {
    const query = event.target.value
    if (query.length < 3) {
        document.getElementById('search-results').innerHTML = ''
        document.getElementById('search-input').classList.remove('has-results')
        clearTimeout(debounceTimer)
        controller?.abort()
        return
    }

    clearTimeout(debounceTimer)
    controller?.abort()
    controller = new AbortController()

    debounceTimer = setTimeout(() => {
        fetch(`/search?q=${query}`, { signal: controller.signal })
            .then(response => response.json())
            .then(data => {
                document.getElementById('search-results').innerHTML = ''
                for (let i = 0; i < data.length; i++) {
                    const li = document.createElement('li')
                    li.classList.add('result-item')
                    li.dataset.termid = data[i][0]
                    li.dataset.termname = data[i][1]
                    li.dataset.synonym = data[i][2]
                    li.innerText = data[i][1]
                    if (data[i][2] != null)
                        li.innerText += ` (${data[i][2]})`
                    li.addEventListener('click', onClickListItem)
                    document.getElementById('search-results').append(li)
                }
                if (0 < data.length)
                    document.getElementById('search-input').classList.add('has-results')

                controller = null
            })
            .catch(console.log)
    }, 300)
}

const onClickListItem = async (event) => {
    if (checkDuplicate(event.target.dataset.termid))
        return

    addSelectedSymptom(event.target.dataset.termid, event.target.dataset.termname)

    const termId = event.target.dataset.termid
    const response = await fetch(`/superterms?term_id=${termId}&limit=1`)
    const superterms = await response.json()

    if (superterms.length == 0)
        return

    while (0 < superterms.length) {
        if (checkDuplicate(superterms[0][0])) {
            superterms.shift()
            continue
        }

        const addSuperterm = confirm(`Add '${superterms[0][1]}' to your list?`)
        if (addSuperterm) {
            addSelectedSymptom(superterms[0][0], superterms[0][1])
        }
        superterms.shift()
    }

    document.getElementById('search-input').value = ''
    document.getElementById('search-input').classList.remove('has-results')
    document.getElementById('search-results').innerHTML = ''
}

const removeSelectedSymptom = (event) => {
    event.target.remove()
    updateAnalyzeButton()
}

const checkDuplicate = (termId) => {
    const li = document.querySelectorAll('#selected-symptoms li')
    for (let i = 0; i < li.length; i++) {
        if (li[i].dataset.termid == termId)
            return true
    }
    return false
}

const addSelectedSymptom = (termId, termName) => {
    const listItem = document.createElement('li')
    listItem.classList.add('selected-symptom')
    listItem.dataset.termid = termId
    listItem.dataset.termname = termName
    listItem.innerText = '➕ ' + termName
    listItem.onclick = removeSelectedSymptom
    const parent = document.querySelector('#selected-symptoms')
    parent.append(listItem)
    updateAnalyzeButton()
}

const updateAnalyzeButton = () => {
    const button = document.querySelector('#analyze-button')
    const li = document.querySelectorAll('#selected-symptoms li')
    button.disabled = li.length == 0
}

const onClickAnalyzeButton = async () => {
    const li = document.querySelectorAll('#selected-symptoms li')
    const termIds = []
    for (let i = 0; i < li.length; i++) {
        termIds.push(li[i].dataset.termid)
    }

    fetch('/disorders?hpo_ids=' + termIds.join(','))
        .then(response => response.json())
        .then(data => {
            const keys = Object.keys(data).sort((a, b) =>
                data[b].reduce((c, d) => c + d[2], 0) - data[a].reduce((c, d) => c + d[2], 0)
            ).slice(0, 30)

            // Draw table
            const table = document.getElementById('result-table')
            {
                table.innerHTML = ''
                const thead = document.createElement('thead')
                const tr = document.createElement('tr')
                const th1 = document.createElement('th')
                tr.append(th1)
                for (let i = 0; i < keys.length; i++) {
                    const th = document.createElement('th')
                    th.scope = 'col'
                    const span = document.createElement('span')
                    span.innerText = keys[i]
                    th.append(span)
                    tr.append(th)
                }
                thead.append(tr)
                table.append(thead)
            }

            const tbody = document.createElement('tbody')
            for (let i = 0; i < termIds.length; i++) {
                const tr = document.createElement('tr')
                const th = document.createElement('th')
                th.scope = 'row'
                th.innerText = `${termIds[i]} ${li[i].dataset.termname}`
                th.classList.add('sort-right')
                tr.append(th)

                for (let j = 0; j < keys.length; j++) {
                    const td = document.createElement('td')
                    ids = data[keys[j]].map((x) => x[0])

                    if (!ids.includes(termIds[i])) {
                        td.innerText = ''
                        tr.append(td)
                        continue
                    }

                    const frequency = data[keys[j]].filter((x) => x[0] == termIds[i])[0][2]

                    if (frequency == 1) // Excluded (0%)
                        td.innerText = '🚫'
                    else if (frequency == 2) // Very rare (<4-1%)
                        td.innerText = '🟫'
                    else if (frequency == 3) // Occasional (29-5%)
                        td.innerText = '🟧'
                    else if (frequency == 4) // Frequent (79-30%)
                        td.innerText = '🟨'
                    else if (frequency == 5) // Very frequent (99-80%)
                        td.innerText = '🟩'
                    else if (frequency == 6) // Obligate (100%)
                        td.innerText = '✅'
                    tr.append(td)
                }
                tbody.append(tr)
            }
            table.append(tbody)

            document.getElementById('result-container').removeAttribute('hidden')
        })
        .catch(console.log)
}

const onSubmitPhenoTagger = async (event) => {
    event.preventDefault()

    const text = event.target[0].value
    const body = {
        'para_overlap': 'true',
        'para_abbr': 'true',
        'para_threshold': '0.95',
        'doc': text
    }

    // Show spinner
    document.getElementById('spinner').classList.remove('hidden')

    const response = await fetch('/biotag', {
        method: 'POST',
        body: JSON.stringify(body),
        headers: {
            'Content-Type': 'application/json'
        }
    }).catch(console.log)
        .then(response => response.json())
        .then(data => data.forEach((x) => checkDuplicate(x[0])
            ? null
            : addSelectedSymptom(x[0], x[1])))

    // Hide spinner
    document.getElementById('spinner').classList.add('hidden')
}

document.getElementById('search-input').addEventListener('input', onInput)
document.getElementById('paragraph-form').addEventListener('submit', onSubmitPhenoTagger)
document.getElementById('analyze-button').addEventListener('click', onClickAnalyzeButton)
