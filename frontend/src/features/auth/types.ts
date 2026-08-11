/**
 * Types local to `auth`.
 *
 * The wire shapes come from `packages/api-types`, generated from the backend's
 * OpenAPI spec — so a change to what the engine returns is a type error here
 * rather than a runtime surprise.
 */

import type { components } from '@realestate-factory/api-types';

export type AuthResponse = components['schemas']['AuthResponse'];
export type SessionUser = components['schemas']['SessionUser'];
export type SignInRequest = components['schemas']['SignInRequest'];
export type SignUpRequest = components['schemas']['SignUpRequest'];

/**
 * Sign-in is two steps, not one. The engine answers a password with either a
 * session or a challenge, and MFA is on by default because accounts here sign
 * documents a bank or a tribunal relies on.
 */
export type AuthStage = 'credentials' | 'mfa' | 'enrolling' | 'authenticated';
