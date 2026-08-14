import { useEffect, useState } from "react"

const PLACEHOLDER_USERNAMES = [
  "torvalds",
  "gvanrossum",
  "dhh",
  "yyx990803",
  "tj",
  "sindresorhus",
  "addyosmani",
  "kentcdodds",
  "dan_abramov",
]

interface UsernameInputProps {
  onSubmit: (username: string) => void
  isLoading?: boolean
}

const UsernameInput = ({ onSubmit, isLoading = false }: UsernameInputProps) => {
  const [value, setValue] = useState("")
  const [placeholderIndex, setPlaceholderIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIndex((i) => (i + 1) % PLACEHOLDER_USERNAMES.length)
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const validate = (username: string): string | null => {
    if (!username) return "Enter a GitHub username"
    if (!/^[a-zA-Z0-9-]{1,39}$/.test(username)) return "Invalid username format"
    if (username.startsWith("-") || username.endsWith("-")) return "Username cannot start or end with a hyphen"
    return null
  }

  const handleSubmit = () => {
    const err = validate(value.trim())
    if (err) {
      setError(err)
      return
    }
    setError(null)
    onSubmit(value.trim())
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit()
  }

  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="flex w-full gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => {
            setValue(e.target.value)
            setError(null)
          }}
          onKeyDown={handleKeyDown}
          placeholder={`try ${PLACEHOLDER_USERNAMES[placeholderIndex]}`}
          disabled={isLoading}
          aria-label="GitHub username"
          className="input flex-1"
          style={{ width: "auto" }}
        />
        <button
          onClick={handleSubmit}
          disabled={isLoading || !value.trim()}
          className="btn btn-primary"
          style={{ whiteSpace: "nowrap" }}
        >
          {isLoading ? "Analyzing…" : "Analyze"}
        </button>
      </div>
      {error && <p className="error-text" style={{ fontSize: "0.8rem", margin: 0 }}>{error}</p>}
    </div>
  )
}

export default UsernameInput
