/*
 * Generated from saved assertion gaps.
 * framework=cunit
 * language=c
 * filename=RQ13_chunk12_missing_test_4.c
 */

#include <CUnit/CUnit.h>
#include "st_support.h"
#include "est_client.h"
#include "est_server.h"
#include "test_utils.h"

/* Shared helpers/fixtures used by exemplar tests: read_binary_file, st_start,
 * est_client_init, est_client_set_server, est_destroy, SLEEP
 */

static void rq13_chunk12_missing_test_4(void)
{
    int rc;
    unsigned char *cacerts = NULL;
    int cacerts_len = 0;
    EST_CTX *ectx = NULL;

    /*
     * Start server with default flags (implicit TA enabled in exemplar usage)
     */
    rc = st_start(US897_SERVER_PORT,
                  US897_SERVER_CERTKEY,
                  US897_SERVER_CERTKEY,
                  "RQ13 test realm",
                  US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
                  US897_TRUST_CERTS,
                  "CA/estExampleCA.cnf",
                  0, 0, 0);
    CU_ASSERT(rc == 0);
    if (rc) return;
    SLEEP(1);

    /*
     * Read client CA certificates (explicit TA data) and create a client
     * context which should succeed when explicit TA data is valid.
     */
    cacerts_len = read_binary_file(CLIENT_UT_CACERT, &cacerts);
    CU_ASSERT(cacerts_len > 0);
    if (cacerts_len <= 0) return;

    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (ectx) {
        est_client_set_server(ectx, US897_SERVER_DOMAIN_NAME, US897_SERVER_PORT, NULL);
        est_destroy(ectx);
        ectx = NULL;
    }

    /*
     * Restart server with the implicit-TA-related flag toggled (last flag=1)
     * to simulate disabling implicit TA and ensure server still starts.
     * The exemplar st_start call used trailing zeros; here we pass 1 to
     * exercise the implicit-TA disable code path as suggested by the gap.
     */
    rc = st_start(US897_SERVER_PORT,
                  US897_SERVER_CERTKEY,
                  US897_SERVER_CERTKEY,
                  "RQ13 test realm",
                  US897_CACERTS_SINGLE_CHAIN_MULT_CERTS,
                  US897_TRUST_CERTS,
                  "CA/estExampleCA.cnf",
                  0, 0, 1);
    CU_ASSERT(rc == 0);
    if (rc) return;
    SLEEP(1);

    /*
     * Re-create client context using the explicit TA data to verify client
     * initialization is still possible (explicit TA DB remains usable).
     */
    ectx = est_client_init(cacerts, cacerts_len, EST_CERT_FORMAT_PEM, client_manual_cert_verify);
    CU_ASSERT(ectx != NULL);
    if (ectx) {
        est_destroy(ectx);
    }

    free(cacerts);
}
