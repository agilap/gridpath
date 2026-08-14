import { BUG_REPORT_URL } from "../../lib/constants"

export default function Footer() {
  return (
    <footer className="app-footer">
      <a className="footer-link" href={BUG_REPORT_URL} target="_blank" rel="noreferrer">
        Report a Bug
      </a>
    </footer>
  )
}
