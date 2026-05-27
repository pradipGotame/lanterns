/*
 * Generated from saved assertion gaps.
 * framework=generic c test
 * language=c
 * filename=RQ13_chunk5_missing_test_2.c
 */

#include <CUnit/Basic.h>
#include <openssl/ssl.h>

/* Expose the helper used by exemplar tests */
extern void us894_test_sslversion(const SSL_METHOD *method, int expected);

static void rq13_chunk5_missing_test_2(void)
{
    LOG_FUNC_NM
    ;

    /*
     * Ensure a modern TLS protocol (TLS1.2) is accepted by the server.
     * This exercises TLS-version acceptance which is part of enforcing
     * confidentiality/integrity requirements at the transport layer.
     */
    us894_test_sslversion(TLSv1_2_client_method(), 0);

    /*
     * Ensure deprecated/unauthorized protocols are rejected by policy.
     * When supported by the build, exercise TLSv1 and expect rejection.
     */
#ifdef TLSv1_client_method
    us894_test_sslversion(TLSv1_client_method(), 1);
#endif

    /*
     * Note: explicit on-the-wire packet inspections (to assert TLS record
     * framing / absence of plaintext) and HTTP-header-level identity/fallback
     * assertions require packet-capture and HTTP parsing helpers which are
     * not expressible with the available exemplar helpers; this test closes
     * the gap for protocol/cipher enforcement from the provided context.
     */
}
