let controller = null // AbortController

const onInput = async (event) => {
    const query = event.target.value
    if (query.length < 3) {
        document.getElementById('search-results').innerHTML = ''
        document.getElementById('search-input').classList.remove('has-results')
        controller?.abort()
        return
    }

    controller?.abort()
    controller = new AbortController()

    fetch(`/search?q=${query}`, { signal: controller.signal }).then(response => response.json())
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

document.getElementById('search-input').addEventListener('input', onInput)
