const commandOutputs = {
  brief: `☀ DAILY PORTFOLIO BRIEF

Tracked value       $42,680
Latest session      +$318  (+0.8%)

WHAT NEEDS REVIEW
● NVDA concentration — 24.6% weight
● AAPL event risk — earnings in 6 days

Use /risk for details or /analyze TICKER.
No order was or can be placed.`,
  risk: `⚠ PORTFOLIO RISK REVIEW

● CONCENTRATION
  NVDA is 24.6% of tracked value.

● DRAWDOWN FROM COST
  TSLA is 18.2% below average cost.
  Recheck the thesis; do not react to price alone.

2 items need review · illustrative data`,
  analyze: `⌕ NVDA REVIEW

Context                 MIXED / NEEDS REVIEW
Latest session          +1.4%
20-session momentum     +4.8%
Annualized volatility   47.2%
RSI (14)                61.8

Compare trend with fundamentals and events.
Technical context is not a recommendation.`,
  portfolio: `▦ PORTFOLIO

AAPL    12 shares    $2,736    19.1%
MSFT     8 shares    $3,360    23.5%
NVDA    40 shares    $3,520    24.6%
Cash                $4,680    32.8%

Tracked value       $14,296
Illustrative data · timestamps shown in the bot`,
};

const output = document.querySelector("#command-output");
const buttons = document.querySelectorAll(".command-button");

buttons.forEach((button) => {
  button.addEventListener("click", () => {
    buttons.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    output.textContent = commandOutputs[button.dataset.command];
  });
});

document.querySelector("#year").textContent = new Date().getFullYear();
