// Lets any page open the chat widget, optionally sending a question (e.g. "Ask about this item").
export const OPEN_CHAT = 'cc:open-chat'

export function openChat(question?: string) {
  window.dispatchEvent(new CustomEvent<string | undefined>(OPEN_CHAT, { detail: question }))
}
