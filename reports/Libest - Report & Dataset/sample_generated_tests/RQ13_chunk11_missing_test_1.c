/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk11_missing_test_1.c
 */

#include <CUnit/CUnit.h>
#include "est.h"
#include <stdlib.h>

void rq13_chunk11_missing_test_1(void)
{
    int rc = 0;
    EST_CTX *ectx = NULL;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;
    unsigned char *rcvd_cacerts = NULL;
    int rcvd_cacerts_len = 0;
    int rv = 0;

    /*
     * Start the server using the multi-chain CA/CRL bundle and trust certs
     * (matches the style of existing tests that configure the server).
     */
    rc = st_start(US897_SERVER_PORT,
                 US897_SERVER_CERTKEY,
                 US897_SERVER_CERTKEY,
                 "RQ13 chunk11 test realm",
                 US897_CACERTS_MULTI_CHAIN_CRLS,
                 US897_TRUST_CERTS,
                 "CA/estExampleCA.cnf",
                 0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;

    /*
     * Read a client-side trust store and create a client context
     * so the client can verify the server and request /cacerts.
     */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);
    if (cacerts_len <= 0) {
        return;
    }

    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (!ectx) {
        free(cacerts);
        return;
    }

    /*
     * Retrieve the CA certificates via the EST /cacerts flow.  A non-zero
     * length indicates subordinate CA certs are available from /cacerts,
     * which supports the server behavior of not needing to include the
     * full chain in the TLS Certificate handshake message.
     */
    rv = est_client_get_cacerts(ectx, &rcvd_cacerts, &rcvd_cacerts_len);
    CU_ASSERT(rv == EST_ERR_NONE);
    CU_ASSERT(rcvd_cacerts_len > 0);

    if (rcvd_cacerts) {
        free(rcvd_cacerts);
    }
    est_destroy(ectx);
    free(cacerts);
}
