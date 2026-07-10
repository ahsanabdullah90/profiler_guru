/**
 * Tests for src/store/contactsStore.ts
 *
 * Covers: setSelectedContact null-safety, client_id/name fallback resolution,
 * and fetchContacts error handling.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Contact } from '@/store/api';

// Helper: create a minimal Contact fixture
function makeContact(overrides: Partial<Contact> = {}): Contact {
  return {
    name: 'Test User',
    client_id: 'uuid-test-001',
    display_name: 'Test Display',
    msg_count: 10,
    last_date: '2024-01-01',
    last_snippet: 'hello',
    avg_msg: 5,
    indexed_chunks: 3,
    rag_progress: 100,
    depth_label: 'Acquaintance',
    depth_color: '#aaa',
    ...overrides,
  };
}

async function freshContactsStore() {
  vi.resetModules();
  // Stub fetch to prevent real network calls
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
    new Response(JSON.stringify([]), { status: 200 }),
  ));
  const { useContactsStore } = await import('@/store/contactsStore');
  return useContactsStore;
}

describe('contactsStore — setSelectedContact', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('sets selectedContact and selectedContactId to null when called with null', async () => {
    const store = await freshContactsStore();
    store.getState().setSelectedContact(null);
    expect(store.getState().selectedContact).toBeNull();
    expect(store.getState().selectedContactId).toBeNull();
  });

  it('resolves client_id when a matching contact is in the list', async () => {
    const store = await freshContactsStore();
    // Manually inject a contact into state
    store.setState({ contacts: [makeContact()] });

    store.getState().setSelectedContact('Test User');
    // Should resolve to client_id
    expect(store.getState().selectedContact).toBe('uuid-test-001');
    expect(store.getState().selectedContactId).toBe('uuid-test-001');
  });

  it('falls back to the contact name when client_id is absent', async () => {
    const store = await freshContactsStore();
    store.setState({
      contacts: [makeContact({ client_id: null })],
    });

    store.getState().setSelectedContact('Test User');
    expect(store.getState().selectedContact).toBe('Test User');
  });

  it('clears messages, analytics and months on contact switch', async () => {
    const store = await freshContactsStore();
    store.setState({
      messages: [{ id: '1', sender: 'A', time: 't', text: 'hi', audio_url: null, audio_status: null, is_self: false }],
      analytics: { avg_msg_weekly: 1, avg_msg_monthly: 4, depth_label: 'x', depth_color: '#x', timeline: [], total_messages: 10, audio_count: 0, audio_ratio: 0 },
      availableMonths: ['2024-01'],
    });

    store.getState().setSelectedContact(null);
    expect(store.getState().messages).toHaveLength(0);
    expect(store.getState().analytics).toBeNull();
    expect(store.getState().availableMonths).toHaveLength(0);
  });
});

describe('contactsStore — fetchContacts', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('pushes an error when the API call fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network error')));

    vi.resetModules();
    const { useContactsStore } = await import('@/store/contactsStore');
    const { useStatusStore } = await import('@/store/statusStore');

    const pushError = vi.spyOn(useStatusStore.getState(), 'pushError');
    await useContactsStore.getState().fetchContacts();

    expect(pushError).toHaveBeenCalledWith(
      expect.stringContaining('Failed to load contacts'),
      'error',
    );
  });
});
