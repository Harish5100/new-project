const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:' ? 'http://127.0.0.1:5000' : '';
let questions = [];
let defaultTime = 30;

// const sounds = {
//     correct: new Audio("sounds/correct.mp3"),
//     wrong: new Audio("sounds/wrong.mp3"),
//     click: new Audio("sounds/click.mp3"),
//     warning: new Audio("sounds/warning.mp3"),
//     win: new Audio("sounds/win.mp3"),
//     lose: new Audio("sounds/lose.mp3")
// };

let current = 0;
let score = 0;
let correctCount = 0;
let wrongCount = 0;
let unansweredCount = 0;
let time;
let timer;
let userAnswers = [];
let hasAnswersData = true;


const qEl = document.getElementById("question");
const optEl = document.getElementById("options");
const timerEl = document.getElementById("timer");
const scoreEl = document.getElementById("score");
const resultBox = document.getElementById("result");
const finalScore = document.getElementById("final-score");
const feedback = document.getElementById("feedback");


function loadQuestion() {
    clearInterval(timer);
    time = defaultTime;
    timerEl.classList.remove("warning");
    
    const nextBtn = document.getElementById("next-btn");
    if (nextBtn) nextBtn.classList.add("hidden");

    const q = questions[current];
    qEl.textContent = q.question;
    optEl.innerHTML = "";

    startTimer();

    q.options.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "option-btn";
        btn.textContent = opt.text;

        btn.onclick = () => handleAnswer(btn, opt.isCorrect);

        optEl.appendChild(btn);
    });
}


function handleAnswer(btn, isCorrect) {
    clearInterval(timer);

    // Record the chosen answer for breakdown
    userAnswers[current] = btn.textContent;

    const buttons = document.querySelectorAll(".option-btn");
    const correctOpt = questions[current].options.find(o => o.isCorrect);

    buttons.forEach(b => {
        b.disabled = true;
        if (b.textContent === correctOpt.text) {
            b.classList.add("correct");
        }
    });

    if (isCorrect) {
        score++;
        correctCount++;
    } else {
        wrongCount++;
        btn.classList.add("wrong");
    }

    scoreEl.textContent = "Score: " + score;

    const nextBtn = document.getElementById("next-btn");
    if (nextBtn) nextBtn.classList.remove("hidden");
}


function nextQuestion() {
    current++;
    if (current < questions.length) {
        loadQuestion();
    } else {
        showResult();
    }
}


function startTimer() {
    timer = setInterval(() => {
        time--;
        timerEl.textContent = time + "s";

        if (time <= 10) {
            timerEl.classList.add("warning");
            if (time === 10) {
                // sounds.warning.play().catch(e => console.log(e)); // Catch to avoid DOMException if page hasn't been interacted with
            }
        }

        if (time <= 0) {
            clearInterval(timer);
            unansweredCount++;
            userAnswers[current] = null; // record as skipped
            nextQuestion();
        }
    }, 1000);
}
 
 
async function showResult() {
    document.getElementById("quiz").classList.add("hidden");
    resultBox.classList.remove("hidden");

    const percent = questions.length > 0 ? Math.round((score / questions.length) * 100) : 0;
    finalScore.textContent = "Score: " + percent + "%";

    document.getElementById("correct-count").textContent = correctCount;
    document.getElementById("wrong-count").textContent = wrongCount;
    document.getElementById("unanswered-count").textContent = unansweredCount;

    if (percent >= 60) {
        feedback.textContent = " Congratulations U Won!";
    } else {
        feedback.textContent = "Try Again";
    }

    // Render question breakdown / explanations
    renderBreakdown();

    const user = JSON.parse(localStorage.getItem('currentUser'));
    if (user) {
        const startTimeRaw = localStorage.getItem('assessmentStartTime');
        const startTime = startTimeRaw ? parseInt(startTimeRaw, 10) : Date.now();
        const timeSpent = Math.floor((Date.now() - startTime) / 1000);
        
        try {
            await fetch(`${API_BASE}/api/results`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: user.username,
                    score: percent,
                    timeSpent: timeSpent,
                    correct: correctCount,
                    wrong: wrongCount,
                    unanswered: unansweredCount,
                    answers: userAnswers
                })
            });
        } catch(e) {
            console.error("Failed to save result", e);
        }
    }
}


function restartQuiz() {
    const urlParams = new URLSearchParams(window.location.search);
    const reviewUsername = urlParams.get('username');
    if (reviewUsername) {
        window.location.href = `dashboard.html?username=${encodeURIComponent(reviewUsername)}`;
    } else {
        window.location.href = 'dashboard.html';
    }
}

function retestQuiz() {
    current = 0;
    score = 0;
    correctCount = 0;
    wrongCount = 0;
    unansweredCount = 0;
    userAnswers = [];
    hasAnswersData = true;
    document.getElementById("quiz").classList.remove("hidden");
    resultBox.classList.add("hidden");
    scoreEl.textContent = "Score: " + score;
    localStorage.setItem('assessmentStartTime', Date.now());
    loadQuestion();
}

function renderBreakdown() {
    const section = document.getElementById('questions-breakdown');
    const list = document.getElementById('breakdown-list');
    if (!section || !list) return;

    list.innerHTML = '';
    questions.forEach(function(q, i) {
        const userAns = userAnswers[i]; // text of the option chosen, or null if skipped
        const correctOpt = q.options.find(function(o) { return o.isCorrect; });
        const isCorrectAns = userAns && correctOpt && userAns === correctOpt.text;
        const isSkipped = !userAns;

        let badgeClass = isSkipped ? 'skipped' : (isCorrectAns ? 'correct' : 'wrong');
        let badgeLabel = isSkipped ? 'Skipped' : (isCorrectAns ? 'Correct' : 'Wrong');

        let optsHtml = '';
        q.options.forEach(function(opt) {
            let cls = 'normal';
            let label = '';
            if (opt.isCorrect) {
                cls = 'correct';
                label = '✔ ';
            } else if (userAns === opt.text && !opt.isCorrect) {
                cls = 'wrong';
                label = '✘ ';
            }
            
            let choiceBadge = '';
            if (userAns === opt.text) {
                const badgeColor = opt.isCorrect ? '#065f46' : '#991b1b';
                const badgeBg = opt.isCorrect ? '#d1fae5' : '#fee2e2';
                choiceBadge = ' <span style="display: inline-block; font-size: 11px; font-weight: 700; background: ' + badgeBg + '; color: ' + badgeColor + '; padding: 2px 6px; border-radius: 4px; margin-left: 8px; border: 1px solid currentColor; vertical-align: middle;">Student\'s Answer</span>';
            }

            optsHtml += '<div class="breakdown-opt ' + cls + '">' +
                label + escHtml(opt.text) + choiceBadge + '</div>';
        });

        let selectionText = '';
        if (hasAnswersData && !isSkipped) {
            if (isCorrectAns) {
                selectionText = '<div style="margin-top: 10px; font-size: 13px; color: #4b5563; font-weight: 600;">Student Answered: <span style="color: #065f46; font-weight: 700; background: #d1fae5; padding: 3px 8px; border-radius: 6px; border: 1px solid #10b981; display: inline-block; vertical-align: middle;">' + escHtml(userAns) + ' (Correct)</span></div>';
            } else {
                selectionText = '<div style="margin-top: 10px; font-size: 13px; color: #4b5563; font-weight: 600;">Student Answered: <span style="color: #991b1b; font-weight: 700; background: #fee2e2; padding: 3px 8px; border-radius: 6px; border: 1px solid #ef4444; display: inline-block; vertical-align: middle;">' + escHtml(userAns) + ' (Wrong)</span></div>';
            }
        }

        let explanationHtml = '';
        if (q.example) {
            explanationHtml = '<div class="breakdown-explanation">💡 ' + escHtml(q.example) + '</div>';
        }

        list.innerHTML += '<div class="breakdown-card">' +
            '<span class="breakdown-badge ' + badgeClass + '">' + badgeLabel + '</span>' +
            '<div class="breakdown-q-title">Q' + (i + 1) + '. ' + escHtml(q.question) + '</div>' +
            '<div class="breakdown-options">' + optsHtml + '</div>' +
            selectionText +
            explanationHtml +
            '</div>';
    });

    section.classList.remove('hidden');
}

function escHtml(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}



async function loadReviewMode(username, idx) {
    try {
        const res = await fetch(`${API_BASE}/api/results/${encodeURIComponent(username)}`);
        if (!res.ok) throw new Error("Could not load results");
        const data = await res.json();
        const attempt = data.history[idx];
        if (!attempt) throw new Error("Attempt not found");

        score = attempt.score;
        correctCount = attempt.correct || 0;
        wrongCount = attempt.wrong || 0;
        unansweredCount = attempt.unanswered || 0;
        hasAnswersData = Array.isArray(attempt.answers) && attempt.answers.length > 0;
        userAnswers = attempt.answers || [];

        // Hide quiz, show result
        document.getElementById("quiz").classList.add("hidden");
        resultBox.classList.remove("hidden");

        finalScore.textContent = "Score: " + attempt.score + "%";
        document.getElementById("correct-count").textContent = correctCount;
        document.getElementById("wrong-count").textContent = wrongCount;
        document.getElementById("unanswered-count").textContent = unansweredCount;

        if (attempt.score >= 60) {
            feedback.textContent = "Congratulations U Won!";
        } else {
            feedback.textContent = "Try Again";
        }

        renderBreakdown();
    } catch (e) {
        console.error("Failed to load review mode", e);
        qEl.textContent = "Failed to load assessment review. " + e.message;
    }
}


async function initQuiz() {
    const user = JSON.parse(localStorage.getItem('currentUser'));
    if (!user) {
        window.location.href = '../index.html';
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const reviewIdxStr = urlParams.get('review');
    const isReviewMode = reviewIdxStr !== null;

    // Students can take the test multiple times, though only their first attempt is saved.
    // Restrictive check removed to allow re-taking.

    try {
        const response = await fetch(`${API_BASE}/api/quiz`);
        const data = await response.json();
        questions = data.questions;
        defaultTime = data.time || 30;
    } catch (e) {
        console.error("Failed to load from backend:", e);
    }
    
    if (questions && questions.length > 0) {
        if (isReviewMode) {
            const reviewUsername = urlParams.get('username') || user.username;
            await loadReviewMode(reviewUsername, parseInt(reviewIdxStr, 10));
        } else {
            loadQuestion();
        }
    } else {
        qEl.textContent = "No questions available. Please configure in Admin.";
    }
}

initQuiz();